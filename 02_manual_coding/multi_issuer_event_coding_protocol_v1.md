# Multi-Issuer Event Coding Protocol v1

Date: 2026-05-22

## Purpose

This protocol defines how P1-F expands the project from USDC-only disclosure events to a multi-issuer disclosure/event index.

## Record Types

- `event`: a dated disclosure, regulatory, or issuer announcement row.
- `source_series`: an official recurring source that must be sampled or extracted into dated events later.

## Event-Date Rule

The preferred event date is publication date, not reserve report date. Rows without a confirmed publication date are not event-study-ready.

## Inclusion Boundary

Rows marked `event_study_ready = 1` may be used for pilot event-window construction. Rows marked `event_study_ready = 0` are source-expansion candidates and must remain out of event-study estimation until the verification queue is resolved.

## Scheduled vs Ad Hoc

- Scheduled: routine monthly, quarterly, daily, or weekly disclosure publication.
- Ad hoc: regulatory action, issuer wind-down announcement, provider change, crisis statement, or other unscheduled disclosure-relevant event.

## Current Claim Boundary

All rows are coded under `RQI_DII_v1.0`. This index supports pilot design and source planning only; final inference requires source verification and multi-issuer coverage completion.
