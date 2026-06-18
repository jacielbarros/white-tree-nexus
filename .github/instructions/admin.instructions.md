# Admin Frontend Instructions — wtnadmin

> Codinome provisorio. Find-replace `wtnadmin` pelo nome real do diretorio frontend.

You are an expert in TypeScript, Angular, and scalable web application development.
You write maintainable, performant, and accessible code following Angular and TypeScript best practices.

## TypeScript Best Practices

- Use strict type checking
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Angular 21 (standalone components — **no NgModules**) |
| UI components | PrimeNG 21 + `@primeuix/themes` (Material preset) |
| State | Angular Signals (`signal()`, `computed()`) |
| Routing | `@angular/router` — routes defined in `src/app/app.routes.ts` |
| Build | `@angular/build:application` (esbuild) |
| Tests | Vitest (native via `@angular/build:unit-test`) |
| DOM env | `happy-dom` |
| Package manager | npm |

## Developer Workflows

```bash
cd wtnadmin
npm start          # dev server -> http://localhost:4200 (hot-reload)
npm run build      # production build -> dist/
npm run watch      # dev build in watch mode
npm test           # Vitest unit tests
ng generate component path/to/my-component   # scaffold new component
```

## Architecture

- **Bootstrapping**: `src/main.ts` -> `appConfig` (`src/app/app.config.ts`) — providers live here (router, PrimeNG theme, error listeners).
- **Root component**: `src/app/app.ts` — uses `RouterOutlet`.
- **Routing**: add routes to the `routes` array in `src/app/app.routes.ts`.
- **Theme**: PrimeNG is globally configured with `Material` preset in `app.config.ts`; do not import theme CSS manually.

## Component Conventions

- All components are **standalone** (`imports: [...]` on the decorator — never `NgModule`).
- Separate files for template/styles: `templateUrl: './foo.html'`, `styleUrl: './foo.css'`.
- Use **Signals** for component state (`signal()`) instead of class properties + `OnChanges`.
- Selector prefix: `app-` (enforced via `angular.json` `prefix`).

## Angular Version Rules (Critical)

- Angular 21: `standalone: true` is DEFAULT. **Never set it explicitly** in decorators.
- Use `input()` / `output()` functions — NOT `@Input()` / `@Output()` decorators.
- Use `computed()` for derived state.
- Use signals (`signal()`) for all mutable local state.
- Use `inject()` — NOT constructor injection.
- Use native control flow: `@if`, `@for`, `@switch` — NOT `*ngIf`, `*ngFor`, `*ngSwitch`.
- Do NOT use `ngClass` — use `[class]` bindings. Do NOT use `ngStyle` — use `[style]` bindings.
- Do NOT use `@HostBinding` / `@HostListener` — use `host: {}` inside the decorator.
- Always set `changeDetection: ChangeDetectionStrategy.OnPush`.
- Prefer `NonNullableFormBuilder` and Reactive Forms over Template-driven forms.
- Use `NgOptimizedImage` for static images (not base64).
- Do NOT name component classes with `Component` suffix (e.g., `RiskList` not `RiskListComponent`).
- Do NOT write arrow functions in templates.

## State Management

- Use signals for local component state; `computed()` for derived state.
- Keep state transformations pure and predictable.
- Do NOT use `mutate` on signals — use `update` or `set`.

## Services

- Single responsibility; `providedIn: 'root'` for singletons.
- Use `inject()` instead of constructor injection.

## Testing Patterns

Tests use Angular `TestBed`. Vitest is the runner (native via `@angular/build:unit-test`) —
use `describe`/`it`/`expect` (Vitest globals, no Jasmine). No `vite.config.ts` or
`test-setup.ts` needed — the builder handles TestBed init, zone.js and DOM environment.

## Path Aliases (tsconfig.json)

```
@app/*           -> ./src/app/*
@environment/*   -> ./src/environments/*
```

## Project Structure

```
wtnadmin/
  src/
    main.ts
    index.html
    environments/
      environment.ts          # prod
      environment.dev.ts      # dev
    assets/
    app/
      app.ts                  # Root component
      app.config.ts           # Application bootstrap providers
      app.routes.ts           # Root routes
      core/                   # Singleton services and app-wide utilities
      pages/                  # Feature modules (lazy-loaded routes)
      shared/                 # Re-usable components, directives, pipes, validators
```

## Backend Integration

O backend roda em `http://localhost:8000` (dev), documentado em `http://localhost:8000/docs`.
Autenticacao: JWT Bearer via `POST /auth/token`; enviar `Authorization: Bearer <token>`.
O token carrega o tenant e o papel do usuario — a UI nunca deve permitir selecionar/operar
dados de outra organizacao. Permissoes do usuario logado: `GET /access-profiles/me/permissions`.
