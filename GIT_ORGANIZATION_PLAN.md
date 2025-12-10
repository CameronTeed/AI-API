# 📁 Git Organization Plan

## Current Structure
```
/home/cameron/ai-api/
├── .git (root repo - tracks ai_orchestrator)
├── ai_orchestrator/ (Python AI - part of root repo)
├── api/ (Java Backend - separate .git)
├── web-app/ (Frontend - separate .git)
└── docs/
```

## Issues
1. Root `.git` is tracking ai_orchestrator
2. `api/` has its own `.git` (separate repo)
3. `web-app/` has its own `.git` (separate repo)
4. This creates a monorepo with nested repos (confusing)

## Recommended Structure

### Option A: Monorepo (Single Root Git)
```
/home/cameron/ai-api/
├── .git (single root repo)
├── ai_orchestrator/
│   ├── .gitignore
│   └── (no .git)
├── api/
│   ├── .gitignore
│   └── (no .git)
├── web-app/
│   ├── .gitignore
│   └── (no .git)
└── docs/
```

### Option B: Separate Repos (Current)
```
/home/cameron/ai-api/
├── ai_orchestrator/ (.git)
├── api/ (.git)
├── web-app/ (.git)
└── docs/
```

## Recommendation
**Option A (Monorepo)** is better because:
- ✅ Single source of truth
- ✅ Easier to track changes across components
- ✅ Simpler CI/CD
- ✅ Atomic commits across all components

## Steps to Implement Option A

1. Remove nested `.git` directories from `api/` and `web-app/`
2. Keep root `.git` as the single source of truth
3. Move ai_orchestrator to be part of root repo
4. Update `.gitignore` files
5. Commit all changes

## Steps to Implement Option B

1. Initialize `.git` in ai_orchestrator
2. Remove root `.git`
3. Keep api/ and web-app/ as separate repos
4. Use git submodules or monorepo tool

---

## Which option do you prefer?
- **Option A**: Single monorepo (recommended)
- **Option B**: Separate repos with submodules


