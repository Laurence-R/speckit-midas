# Tasks: Modernize SaaS UI Tone and Layout

**Input**: Design documents from `/specs/003-modernize-saas-ui/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: This feature focuses on implementation, gate verification, and quantitative acceptance.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Build acceptance and quantification scaffolding.

- [X] T001 Create theme audit checklist at specs/003-modernize-saas-ui/checklists/theme-audit.md
- [X] T002 Create contrast check script at scripts/check_ui_contrast.py
- [X] T003 [P] Create spacing token check script at scripts/check_spacing_tokens.py
- [X] T004 Create UX scoring protocol at specs/003-modernize-saas-ui/checklists/ux-scoring-protocol.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared theme/layout base and constitution gates.

**CRITICAL**: No user story work starts before this phase is complete.

- [X] T005 Define semantic dual-theme roles and spacing tokens in src/midas/ui/theme.py
- [X] T006 [P] Add shared style token access module in src/midas/ui/style_tokens.py
- [X] T007 Wire theme and spacing token apply entry in src/midas/ui/app_window.py
- [X] T008 [P] Create UI boundary gate script in scripts/check_ui_boundary.py
- [X] T009 [P] Update theme contract to align token naming in specs/003-modernize-saas-ui/contracts/ui-theme-contract.md
- [X] T010 Execute Desktop Framework Gate and Provider Boundary Gate; record in specs/003-modernize-saas-ui/checklists/theme-audit.md
- [X] T011 Create completion-rate baseline protocol in specs/003-modernize-saas-ui/checklists/completion-rate-protocol.md
- [X] T012 Execute pre-change completion-rate baseline; record in specs/003-modernize-saas-ui/checklists/completion-rate-baseline.md

**Checkpoint**: Theme foundation, gate verification, and baseline are ready.

---

## Phase 3: User Story 1 - Professional First Screen (Priority: P1) MVP

**Goal**: Home and shell visual language reaches modern SaaS quality in dark/light.

**Independent Test**: Validate shell/navigation/content/status on startup.

### Implementation for User Story 1

- [X] T013 [P] [US1] Update app shell backgrounds and container layering in src/midas/ui/app_window.py
- [X] T014 [P] [US1] Apply new navigation palette and typography hierarchy in src/midas/ui/components/sidebar_nav.py
- [X] T015 [P] [US1] Apply status bar palette and message hierarchy in src/midas/ui/components/status_bar.py
- [X] T016 [P] [US1] Apply market overview card theme tone in src/midas/ui/components/market_overview_card.py
- [X] T017 [P] [US1] Apply event list visual hierarchy and typography in src/midas/ui/components/event_list_item.py
- [X] T018 [US1] Adjust dashboard section heading and information hierarchy in src/midas/ui/pages/dashboard_page.py
- [X] T019 [US1] Record US1 dark/light acceptance in specs/003-modernize-saas-ui/checklists/theme-audit.md

**Checkpoint**: First-screen professionalism is independently demonstrable.

---

## Phase 4: User Story 2 - Higher Information Density (Priority: P2)

**Goal**: Reduce excessive whitespace with medium-high density while preserving readability.

**Independent Test**: Check spacing rhythm on dashboard, stock detail, and watchlist.

### Implementation for User Story 2

- [X] T020 [P] [US2] Apply stock detail spacing token rhythm in src/midas/ui/pages/stock_detail_page.py
- [X] T021 [P] [US2] Apply watchlist spacing token rhythm in src/midas/ui/pages/watchlist_page.py
- [X] T022 [P] [US2] Apply settings spacing token rhythm in src/midas/ui/pages/settings_page.py
- [X] T023 [P] [US2] Apply resource monitor spacing token rhythm in src/midas/ui/pages/resource_monitor_page.py
- [X] T024 [P] [US2] Adjust event card density and inner padding in src/midas/ui/components/stock_event_card.py
- [X] T025 [P] [US2] Adjust financial metric row density and rhythm in src/midas/ui/components/financial_metric_row.py
- [X] T026 [US2] Align dashboard container rhythm to medium-high density in src/midas/ui/pages/dashboard_page.py
- [X] T027 [US2] Execute spacing token checks and record in specs/003-modernize-saas-ui/checklists/theme-audit.md

**Checkpoint**: Medium-high density target passes independently.

---

## Phase 5: User Story 3 - Clear Interaction and Semantic States (Priority: P3)

**Goal**: Keep interaction and semantic states clear and consistent in the new theme.

**Independent Test**: Validate default/hover/focus/disabled and semantic color mappings.

### Implementation for User Story 3

- [X] T028 [P] [US3] Implement interaction states for buttons/inputs in src/midas/ui/pages/watchlist_page.py
- [X] T029 [P] [US3] Implement interaction-state consistency in src/midas/ui/pages/settings_page.py
- [X] T030 [P] [US3] Implement semantic status mapping in src/midas/ui/components/stock_event_card.py
- [X] T031 [P] [US3] Implement semantic status mapping in src/midas/ui/pages/resource_monitor_page.py
- [X] T032 [US3] Unify dark/light interaction-state token rules in src/midas/ui/theme.py
- [X] T033 [US3] Record US3 interaction/semantic acceptance in specs/003-modernize-saas-ui/checklists/theme-audit.md

**Checkpoint**: Interaction and semantic states pass independent acceptance.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Consolidate cross-story consistency, gate evidence, and quantitative acceptance.

- [X] T034 [P] Update implementation and acceptance steps in specs/003-modernize-saas-ui/quickstart.md
- [X] T035 [P] Backfill final decisions and constraints in specs/003-modernize-saas-ui/research.md
- [X] T036 Execute WCAG AA contrast sampling and record in specs/003-modernize-saas-ui/checklists/theme-audit.md
- [X] T037 Execute cross-page dark/light consistency sampling and record in specs/003-modernize-saas-ui/checklists/theme-audit.md
- [X] T038 Execute spacing token pass-rate sampling and record in specs/003-modernize-saas-ui/checklists/theme-audit.md
- [X] T039 Execute UX scoring protocol and record in specs/003-modernize-saas-ui/checklists/ux-scoring-results.md
- [X] T040 Execute post-change completion-rate measurement and compare to baseline in specs/003-modernize-saas-ui/checklists/completion-rate-comparison.md
- [X] T041 Execute unit tests and append final acceptance summary in specs/003-modernize-saas-ui/checklists/theme-audit.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: depends on Phase 1 and blocks all stories.
- **Phase 3-5 (User Stories)**: depend on Phase 2.
- **Phase 6 (Polish)**: depends on all target user stories complete.

### User Story Dependencies

- **US1 (P1)**: first executable story after foundational.
- **US2 (P2)**: depends on token foundation and US1 style baseline.
- **US3 (P3)**: depends on token foundation; can overlap with late US2 if file-isolated.

### Within Each User Story

- Apply tokens first, then tune pages/components.
- Component-level updates before page composition updates.
- Record acceptance immediately after each story.

---

## Notes

- Tasks include gate verification and quantitative acceptance (completion-rate baseline, scoring protocol).
- Scope remains UI-only and does not change data flow layers.
- [P] denotes tasks that can run in parallel on isolated files.
