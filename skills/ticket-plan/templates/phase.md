---
number: {phaseNumber}
title: {phaseName}
activity: {activity}
estimate: {phaseHours}
depends_on: [{dependencies}]
projects: [{projects}]
---

# Phase {phaseNumber}: {phaseName}

> Part of the [plan](plan.md) for #{id}: {title}

**Scope:** <!-- one sentence describing what this phase achieves on its own -->

## Prerequisites

<!-- Only what this phase alone needs; a prerequisite several phases share belongs to phase 0. Omit the section when there is none. -->

- [ ] <!-- a prerequisite, e.g. an environment variable set in every target environment, a feature flag, a package in the internal feed -->

## Steps

### Step {phaseNumber}.1

**Status:** {status} <!-- Pending or Done on a first run; ticket-common/STATUS.md has the vocabulary and the note rules -->

**Target:** `{target}`

**Artifacts:** —

<!-- what to do and why, specific enough to act on -->

### Step {phaseNumber}.2

**Status:** {status}

**Target:** `{target}`

**Artifacts:** —

<!-- what to do and why, specific enough to act on -->

### Step {phaseNumber}.M

...
