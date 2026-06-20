import { Routes } from '@angular/router';

import { authGuard, permissionGuard } from '@app/core/guards';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('@app/pages/login/login').then((m) => m.Login) },
  {
    path: 'forgot',
    loadComponent: () => import('@app/pages/password/forgot-password').then((m) => m.ForgotPassword),
  },
  {
    path: 'reset',
    loadComponent: () => import('@app/pages/password/reset-password').then((m) => m.ResetPassword),
  },
  {
    path: 'accept',
    loadComponent: () => import('@app/pages/invite-accept/invite-accept').then((m) => m.InviteAccept),
  },
  {
    path: 'app',
    canActivate: [authGuard],
    loadComponent: () => import('@app/pages/shell/shell').then((m) => m.Shell),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'organizations' },
      {
        path: 'organizations',
        loadComponent: () =>
          import('@app/pages/organizations/organizations').then((m) => m.Organizations),
      },
      {
        path: 'users',
        canActivate: [permissionGuard('view_organization')],
        loadComponent: () => import('@app/pages/users/users').then((m) => m.Users),
      },
      {
        path: 'diagnostic',
        canActivate: [permissionGuard('view_context')],
        loadComponent: () => import('@app/pages/diagnostic/diagnostic').then((m) => m.DiagnosticPage),
      },
      {
        path: 'context-analysis',
        canActivate: [permissionGuard('view_context')],
        loadComponent: () =>
          import('@app/pages/context-analysis/context-analysis').then((m) => m.ContextAnalysisPage),
      },
      {
        path: 'stakeholders',
        canActivate: [permissionGuard('view_context')],
        loadComponent: () => import('@app/pages/stakeholders/stakeholders').then((m) => m.StakeholdersPage),
      },
      {
        path: 'scope',
        canActivate: [permissionGuard('view_context')],
        loadComponent: () => import('@app/pages/scope/scope').then((m) => m.ScopePage),
      },
      {
        path: 'context-overview',
        canActivate: [permissionGuard('view_context')],
        loadComponent: () =>
          import('@app/pages/context-overview/context-overview').then((m) => m.ContextOverviewPage),
      },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'app' },
  { path: '**', redirectTo: 'app' },
];
