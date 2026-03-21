# Frontend — Next.js 14

## Pages

```
frontend/app/
├── page.tsx                    # Landing / redirect to dashboard
├── auth/
│   └── callback/page.tsx       # Supabase OAuth callback
├── onboarding/
│   └── page.tsx                # First-time setup
├── dashboard/
│   └── page.tsx                # Job tracker (main view)
├── apply/
│   ├── page.tsx                # URL paste + instructions input
│   └── review/[id]/page.tsx    # Resume diff + approval gate
├── prepare/
│   └── page.tsx                # Daily prep session
├── prep/[applicationId]/
│   └── page.tsx                # Interview prep for specific role
└── profile/
    └── page.tsx                # Skill graph + settings
```

---

## Page: Apply (`/apply`)

**Flow:**
1. User pastes job URL
2. On paste: call `POST /applications/check` → show status if duplicate
3. If new: show instructions text area + "Start applying" button
4. On submit: call `POST /applications/start` → redirect to `/apply/review/[id]`
5. Review page polls `GET /applications/:id/status` every 3 seconds while processing
6. When `status = review_pending`: show resume diff (approve / edit / discard)
7. On approve: call `POST /applications/:id/approve` → shows form fill progress

**Components:**
```tsx
<URLInput />           // paste field with dedup check on blur
<DuplicateAlert />     // shown if role already in tracker
<InstructionsInput />  // optional free text
<ProcessingStatus />   // step indicator while agent works
<ResumeDiff />         // side-by-side or unified diff view
<ChangesBadge />       // "23% changed from master resume"
<ApprovalButtons />    // Approve / Edit / Discard
```

---

## Page: Dashboard (`/dashboard`)

**Job tracker.** Kanban-style columns by status, or list view.

**Columns:** Processing → Applied → Viewed → Interview → Offer / Rejected

**Each card shows:**
- Company name + role title
- Status + days since applied
- JD overlap score badge
- Last event (e.g. "Interview invite — 2 days ago")
- Quick actions: View prep plan / View resume / Open job URL

**Realtime:** Subscribe to Supabase Realtime on `tracker_events` table.
Cards update live when Gmail monitor detects a new email.

```tsx
<TrackerBoard>
  <StatusColumn status="applied" applications={[...]} />
  <StatusColumn status="interview" applications={[...]} />
  ...
</TrackerBoard>

// or list view toggle
<TrackerList applications={[...]} />

// Detail drawer on card click
<ApplicationDrawer applicationId={id}>
  <EventTimeline events={[...]} />
  <ResumePreview resumeId={id} />
  <PrepPlanLink applicationId={id} />
</ApplicationDrawer>
```

---

## Page: Prepare (`/prepare`)

**Daily 20-min skill building session.**

**Flow:**
1. Load today's topic via `GET /prepare/today`
2. Show topic name, category, current depth
3. Show concept brief (collapsible — encourage user to think first)
4. Show questions one at a time
5. User writes/thinks their answer, then reveals model answer
6. User self-rates each question
7. On submit all ratings: `POST /prepare/today/rate`
8. Show updated depth + streak + what's due tomorrow

```tsx
<PrepHeader topic={topic} category={category} streak={streak} />
<ConceptBrief text={brief} />  // collapsible

<QuestionCard
  question={question}
  onReveal={() => showAnswer()}
  modelAnswer={answer}          // hidden until user clicks "See answer"
/>

<RatingButtons
  onRate={(rating) => setRating(questionId, rating)}
/>
// 'Got it ✓' | 'Unsure ~' | 'Missed ✗'

<SessionSummary
  ratings={ratings}
  depthChange={depthChange}
  nextReviewCount={n}
/>
```

---

## Page: Interview Prep (`/prep/[applicationId]`)

**Triggered when Gmail detects an interview invite.**
User gets a notification in dashboard. Links here.

**Sections:**
1. **Interview summary** — type, date, what to expect
2. **Day-by-day plan** — accordion, one day at a time
3. **STAR stories** — expandable, user's own project mapped to behavioural themes
4. **Claims to defend** — bullets from their submitted resume, with prep notes
5. **Gap topics** — things to study that aren't in their skill graph
6. **Resources** — curated links from research

```tsx
<PrepHeader
  company={company}
  role={role}
  interviewDate={date}
  daysRemaining={n}
  interviewType={['system_design', 'behavioural']}
/>

<PrepDayAccordion days={prepPlan.days} />

<STARStories stories={starStories} />

<ClaimsToDefend claims={claimsToDefend} />

<ResourceList resources={resources} />
```

---

## Page: Profile (`/profile`)

**Skill graph visualisation + settings.**

**Sections:**
1. **Skill graph** — grouped by category, depth bars, source tags
2. **Target roles** — edit, add/remove
3. **Connections** — GitHub connected ✓, LinkedIn URL, Portfolio URL, Gmail connected ✓
4. **Addresses** — saved addresses for location matching
5. **Master resume** — view, re-upload

```tsx
<SkillGrid categories={['cs_fundamentals', 'system_design', 'stack', 'behavioural']}>
  <SkillCard
    name="Redis"
    depth={4}
    sources={['github', 'linkedin']}
    interviewDefensible={true}
    onNudge={(direction) => adjustDepth(skill, direction)}  // +1 / -1
  />
</SkillGrid>

<TargetRolesEditor roles={targetRoles} />
<IntegrationsPanel />
<ResumeUploader />
```

---

## State management

**TanStack Query** for all server state.

```tsx
// Key query patterns

// Poll application status during processing
const { data } = useQuery({
  queryKey: ['application-status', applicationId],
  queryFn: () => api.getApplicationStatus(applicationId),
  refetchInterval: (data) =>
    data?.status === 'processing' ? 3000 : false,   // stop polling when done
})

// Today's prep session
const { data: prepSession } = useQuery({
  queryKey: ['prepare-today'],
  queryFn: () => api.getPrepToday(),
  staleTime: 1000 * 60 * 60,   // fresh for 1 hour
})

// Mutations
const approveMutation = useMutation({
  mutationFn: (resumeText) => api.approveApplication(applicationId, resumeText),
  onSuccess: () => {
    queryClient.invalidateQueries(['application', applicationId])
    router.push('/dashboard')
  }
})
```

**Supabase Realtime** for live tracker updates:
```tsx
useEffect(() => {
  const channel = supabase
    .channel('tracker-updates')
    .on('postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'tracker_events', filter: `user_id=eq.${userId}` },
      (payload) => {
        queryClient.invalidateQueries(['applications'])
        toast.success(`${payload.new.event_type} — ${payload.new.metadata?.company}`)
      }
    )
    .subscribe()

  return () => supabase.removeChannel(channel)
}, [userId])
```

---

## Notifications

Use `sonner` (toast library) for all agent events:

```tsx
// Application submitted
toast.success("Applied to Notion — Senior Backend Engineer")

// Interview invite detected
toast("Interview invite from Stripe", {
  description: "Prep plan generated. 6 days to go.",
  action: { label: "View plan", onClick: () => router.push(`/prep/${appId}`) }
})

// Rejection detected
toast.info("No update from Linear (90 days). Resume archived.")

// Needs action
toast.warning("Agent needs your help", {
  description: "CAPTCHA on Workday. Click to finish manually.",
  action: { label: "Open", onClick: () => window.open(url) }
})
```

---

## Supabase client (frontend)

```tsx
// frontend/lib/supabase.ts
import { createBrowserClient } from '@supabase/ssr'

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

```tsx
// frontend/lib/api.ts — backend calls (goes to localhost:8000)
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiFetch(path: string, options?: RequestInit) {
  const { data: { session } } = await supabase.auth.getSession()
  return fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session?.access_token}`,
      ...options?.headers,
    }
  })
}
```
