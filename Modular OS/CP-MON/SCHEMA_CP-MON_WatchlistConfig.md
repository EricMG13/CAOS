<!-- SCHEMA_CP-MON_WatchlistConfig | v1.0 | 2026-06-08 -->
# SCHEMA_CP-MON_WatchlistConfig — Watchlist Configuration Specification

## 2.1 Purpose

The Watchlist Configuration defines how issuers are grouped, prioritised, scheduled, and monitored in WATCHLIST_SWEEP and EVENT_TRIGGERED modes. A watchlist is a persistent, versioned collection of issuers with per-issuer monitoring parameters.

---

## 2.2 Watchlist Object

```json
{
  "$id": "CP-MON-WatchlistConfig-v1.0",
  "type": "object",
  "required": ["watchlist_id", "watchlist_name", "owner", "issuers", "schedule", "created", "last_updated"],
  "properties": {
    "watchlist_id": {
      "type": "string",
      "pattern": "^WL-[A-Z0-9]+-\\d{3}$",
      "description": "Unique watchlist identifier. Format: WL-{SHORTNAME}-{NNN}."
    },
    "watchlist_name": {
      "type": "string",
      "description": "Human-readable name (e.g., HY Software Coverage, Distressed Watch)."
    },
    "owner": {
      "type": "string",
      "description": "Analyst or team ID owning the watchlist."
    },
    "description": {
      "type": "string",
      "description": "Purpose and scope of the watchlist."
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Taxonomy tags: sector, strategy, fund, etc."
    },
    "issuers": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/WatchlistIssuer" }
    },
    "schedule": { "$ref": "#/$defs/WatchlistSchedule" },
    "alert_config": { "$ref": "#/$defs/WatchlistAlertConfig" },
    "output_config": { "$ref": "#/$defs/WatchlistOutputConfig" },
    "access_control": { "$ref": "#/$defs/WatchlistAccess" },
    "version": { "type": "integer", "minimum": 1 },
    "created": { "type": "string", "format": "date-time" },
    "last_updated": { "type": "string", "format": "date-time" },
    "status": { "type": "string", "enum": ["active", "paused", "archived"], "default": "active" }
  }
}
```

---

## 2.3 WatchlistIssuer Object

Each issuer entry in the watchlist carries per-issuer overrides:

```json
{
  "$defs": {
    "WatchlistIssuer": {
      "type": "object",
      "required": ["issuer_id", "priority"],
      "properties": {
        "issuer_id": {
          "type": "string",
          "description": "CPMON-{NAME}-{NNN} reference to IssuerRegistry."
        },
        "display_name": { "type": "string" },
        "priority": {
          "type": "string",
          "enum": ["critical", "high", "medium", "low"],
          "default": "medium",
          "description": "Monitoring intensity. Critical issuers run first, with tighter thresholds."
        },
        "added_date": { "type": "string", "format": "date" },
        "added_by": { "type": "string" },
        "reason": {
          "type": "string",
          "description": "Why issuer was added (e.g., new position, rating watch, maturity wall 2027)."
        },
        "position_context": {
          "type": "object",
          "properties": {
            "held": { "type": "boolean", "description": "Whether the fund currently holds a position." },
            "instruments": { "type": "array", "items": { "type": "string" }, "description": "Instrument identifiers held." },
            "notional_usd_mm": { "type": ["number", "null"], "description": "Approximate position size for sizing context." },
            "strategy": { "type": "string", "description": "e.g., core HY, opportunistic, CLO warehouse, short." }
          }
        },
        "overrides": {
          "type": "object",
          "description": "Per-issuer parameter overrides.",
          "properties": {
            "time_window": { "type": "string", "description": "Override default window (e.g., 7d for distressed)." },
            "alert_threshold": { "type": "number", "description": "Override default 0.60 (e.g., 0.40 for new coverage)." },
            "source_filter": { "type": "array", "items": { "type": "string" }, "description": "Override source categories." },
            "custom_keywords": { "type": "array", "items": { "type": "string" }, "description": "Additional search terms beyond aliases." },
            "suppress_themes": { "type": "array", "items": { "type": "string" }, "description": "Fragility groups to deprioritise (e.g., Macro for idiosyncratic-only monitoring)." }
          }
        },
        "monitoring_triggers": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Active CP-2B-MON-xxx trigger IDs."
        },
        "review_date": {
          "type": ["string", "null"],
          "format": "date",
          "description": "Next scheduled review date. Null = continuous."
        },
        "status": {
          "type": "string",
          "enum": ["active", "paused", "pending_removal"],
          "default": "active"
        }
      }
    }
  }
}
```

---

## 2.4 Priority Tiers and Behaviour

| Priority | Sweep Order | Default Window | Default Threshold | Alert Routing | Heatmap Colour |
|---|---|---|---:|---|---|
| **Critical** | First | 7d | 0.40 | All channels + immediate push | Red |
| **High** | Second | 14d | 0.50 | Teams + email + dashboard | Orange |
| **Medium** | Third | 30d | 0.60 | Daily briefing + dashboard | Yellow |
| **Low** | Last | 30d | 0.70 | Weekly digest only | Grey |

**Priority escalation rules:**
- Issuer accumulates >=3 Material signals in 30d -> auto-escalate to next priority tier
- Rating downgrade or CreditWatch Negative -> auto-escalate to Critical
- Position size > 2% of fund NAV -> minimum priority = High
- Maturity wall within 18 months -> minimum priority = High

---

## 2.5 Schedule Configuration

```json
{
  "$defs": {
    "WatchlistSchedule": {
      "type": "object",
      "required": ["sweep_frequency"],
      "properties": {
        "sweep_frequency": {
          "type": "string",
          "enum": ["hourly", "daily", "twice_daily", "weekly", "custom_cron"],
          "default": "daily"
        },
        "sweep_time_utc": {
          "type": "string",
          "default": "06:00",
          "description": "Primary sweep time in UTC."
        },
        "secondary_sweep_time_utc": {
          "type": ["string", "null"],
          "description": "For twice_daily. e.g., 18:00."
        },
        "custom_cron": {
          "type": ["string", "null"],
          "description": "Cron expression for custom_cron frequency."
        },
        "timezone_display": {
          "type": "string",
          "default": "Europe/London",
          "description": "Timezone for analyst-facing schedule display."
        },
        "skip_weekends": {
          "type": "boolean",
          "default": false,
          "description": "Skip Saturday/Sunday sweeps."
        },
        "skip_holidays": {
          "type": "array",
          "items": { "type": "string", "format": "date" },
          "description": "Dates to skip (e.g., bank holidays)."
        },
        "event_triggered_enabled": {
          "type": "boolean",
          "default": true,
          "description": "Enable EVENT_TRIGGERED mode for this watchlist."
        }
      }
    }
  }
}
```

---

## 2.6 Alert Configuration

```json
{
  "$defs": {
    "WatchlistAlertConfig": {
      "type": "object",
      "properties": {
        "channels": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["channel_type", "tiers"],
            "properties": {
              "channel_type": { "type": "string", "enum": ["teams", "email", "dashboard", "sms"] },
              "webhook_url": { "type": ["string", "null"] },
              "recipients": { "type": "array", "items": { "type": "string" } },
              "tiers": { "type": "array", "items": { "type": "string", "enum": ["Critical", "Material", "Noteworthy"] } }
            }
          }
        },
        "throttle": {
          "type": "object",
          "properties": {
            "max_critical_per_issuer_24h": { "type": "integer", "default": 5 },
            "cluster_cooldown_hours": { "type": "integer", "default": 4 },
            "quiet_hours_start": { "type": "string", "default": "22:00" },
            "quiet_hours_end": { "type": "string", "default": "06:00" },
            "quiet_hours_exempt_tiers": { "type": "array", "default": ["Critical"] }
          }
        },
        "digest_schedule": {
          "type": "object",
          "properties": {
            "daily_briefing_time_utc": { "type": "string", "default": "07:00" },
            "weekly_digest_day": { "type": "string", "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "default": "Monday" },
            "weekly_digest_time_utc": { "type": "string", "default": "07:00" }
          }
        }
      }
    }
  }
}
```

---

## 2.7 Output Configuration

```json
{
  "$defs": {
    "WatchlistOutputConfig": {
      "type": "object",
      "properties": {
        "briefing_format": { "type": "string", "enum": ["md", "docx", "md+json", "all"], "default": "md+json" },
        "heatmap_format": { "type": "string", "enum": ["json", "html", "powerbi"], "default": "html" },
        "auto_save_path": {
          "type": "string",
          "default": "~/CreditPulse/watchlists/{watchlist_slug}/",
          "description": "Root path for all watchlist outputs."
        },
        "sector_digest_enabled": { "type": "boolean", "default": true },
        "cross_issuer_clustering": { "type": "boolean", "default": true },
        "include_logged_signals": { "type": "boolean", "default": false, "description": "Include Logged-tier signals in output." },
        "max_briefing_issuers": { "type": "integer", "default": 50, "description": "Cap per sweep run." }
      }
    }
  }
}
```

---

## 2.8 Access Control

```json
{
  "$defs": {
    "WatchlistAccess": {
      "type": "object",
      "properties": {
        "owner": { "type": "string" },
        "editors": { "type": "array", "items": { "type": "string" } },
        "viewers": { "type": "array", "items": { "type": "string" } },
        "visibility": { "type": "string", "enum": ["private", "team", "firm"], "default": "team" }
      }
    }
  }
}
```

---

## 2.9 Watchlist Lifecycle

| Action | Trigger | Effect |
|---|---|---|
| **Create** | Analyst creates via UI / API / CLI | New WL-xxx-001 with version 1 |
| **Add issuer** | /watchlist add [issuer] --priority high --reason "new position" | Resolver runs Step A; IssuerRecord created/linked; version incremented |
| **Remove issuer** | /watchlist remove [issuer] | Status -> pending_removal; archived after next sweep confirms no open alerts |
| **Pause issuer** | /watchlist pause [issuer] | Status -> paused; skipped in sweep; alerts suppressed |
| **Pause watchlist** | /watchlist pause | Entire watchlist status -> paused |
| **Archive watchlist** | /watchlist archive | Status -> archived; no sweeps; historical data preserved |
| **Clone watchlist** | /watchlist clone [source_wl] --name "New WL" | Deep copy with new ID and version 1 |
| **Merge watchlists** | /watchlist merge [wl_a] [wl_b] | Union of issuers; priority = max of both; version 1 |

---

## 2.10 Complete Watchlist Example

```json
{
  "watchlist_id": "WL-HYSW-001",
  "watchlist_name": "HY Software Coverage",
  "owner": "eric.minsehimbe",
  "description": "Core high-yield software issuers monitored for the leveraged credit fund.",
  "tags": ["HY", "software", "TMT", "leveraged_loans"],
  "issuers": [
    {
      "issuer_id": "CPMON-VEEAM-001",
      "display_name": "Veeam Software / VS Buyer LLC",
      "priority": "critical",
      "added_date": "2026-01-15",
      "added_by": "eric.minsehimbe",
      "reason": "Core position; post-acquisition integration monitoring",
      "position_context": {
        "held": true,
        "instruments": ["TLB", "Secured Notes"],
        "notional_usd_mm": 12.5,
        "strategy": "core HY"
      },
      "overrides": {
        "time_window": "14d",
        "alert_threshold": 0.45,
        "custom_keywords": ["Securiti AI", "ObjectFirst", "data protection market"]
      },
      "monitoring_triggers": ["CP-2B-MON-001", "CP-2B-MON-005", "CP-2B-MON-008"],
      "review_date": "2026-07-15",
      "status": "active"
    },
    {
      "issuer_id": "CPMON-SKECHERS-001",
      "display_name": "Skechers U.S.A.",
      "priority": "medium",
      "added_date": "2026-03-01",
      "added_by": "eric.minsehimbe",
      "reason": "Sector comparison; consumer discretionary exposure",
      "position_context": {
        "held": false,
        "instruments": [],
        "notional_usd_mm": null,
        "strategy": "research coverage"
      },
      "overrides": {},
      "monitoring_triggers": [],
      "review_date": "2026-09-01",
      "status": "active"
    }
  ],
  "schedule": {
    "sweep_frequency": "daily",
    "sweep_time_utc": "06:00",
    "secondary_sweep_time_utc": null,
    "timezone_display": "Europe/London",
    "skip_weekends": false,
    "event_triggered_enabled": true
  },
  "alert_config": {
    "channels": [
      { "channel_type": "teams", "webhook_url": "https://outlook.office.com/webhook/...", "recipients": [], "tiers": ["Critical"] },
      { "channel_type": "email", "recipients": ["analyst@firm.com", "manager@firm.com"], "tiers": ["Critical", "Material"] },
      { "channel_type": "dashboard", "webhook_url": null, "recipients": [], "tiers": ["Critical", "Material", "Noteworthy"] }
    ],
    "throttle": {
      "max_critical_per_issuer_24h": 5,
      "cluster_cooldown_hours": 4,
      "quiet_hours_start": "22:00",
      "quiet_hours_end": "06:00",
      "quiet_hours_exempt_tiers": ["Critical"]
    },
    "digest_schedule": {
      "daily_briefing_time_utc": "07:00",
      "weekly_digest_day": "Monday",
      "weekly_digest_time_utc": "07:00"
    }
  },
  "output_config": {
    "briefing_format": "md+json",
    "heatmap_format": "html",
    "auto_save_path": "~/CreditPulse/watchlists/hy-software-coverage/",
    "sector_digest_enabled": true,
    "cross_issuer_clustering": true,
    "include_logged_signals": false,
    "max_briefing_issuers": 50
  },
  "access_control": {
    "owner": "eric.minsehimbe",
    "editors": ["paul-antoine.conti"],
    "viewers": ["matthieu.dehen", "stanislav.seltser"],
    "visibility": "team"
  },
  "version": 3,
  "created": "2026-01-15T08:00:00Z",
  "last_updated": "2026-06-08T10:00:00Z",
  "status": "active"
}
```

---

## 2.11 Watchlist Heatmap Output Schema

```json
{
  "$id": "CP-MON-WatchlistHeatmap-v1.0",
  "type": "object",
  "required": ["watchlist_id", "sweep_run_id", "timestamp", "issuers"],
  "properties": {
    "watchlist_id": { "type": "string" },
    "sweep_run_id": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "issuers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "issuer_id": { "type": "string" },
          "display_name": { "type": "string" },
          "priority": { "type": "string" },
          "signal_counts": {
            "type": "object",
            "properties": {
              "critical": { "type": "integer" },
              "material": { "type": "integer" },
              "noteworthy": { "type": "integer" },
              "logged": { "type": "integer" }
            }
          },
          "max_score": { "type": "number" },
          "dominant_cluster": { "type": ["string", "null"] },
          "dominant_theme": { "type": ["string", "null"] },
          "delta_flags": { "type": "array", "items": { "type": "string" } },
          "priority_change": { "type": ["string", "null"], "enum": ["escalated", "de-escalated", null] },
          "last_signal_date": { "type": "string", "format": "date" }
        }
      }
    },
    "sector_clusters": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "sector": { "type": "string" },
          "theme": { "type": "string" },
          "issuer_count": { "type": "integer" },
          "signal_count": { "type": "integer" },
          "max_score": { "type": "number" }
        }
      }
    }
  }
}
```

<!-- END SCHEMA_CP-MON_WatchlistConfig -->
