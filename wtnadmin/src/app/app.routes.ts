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
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () => import('@app/pages/dashboard/dashboard').then((m) => m.DashboardPage),
      },
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
      {
        path: 'form-templates',
        canActivate: [permissionGuard('view_form')],
        loadComponent: () =>
          import('@app/pages/form-templates/form-templates').then((m) => m.FormTemplatesPage),
      },
      {
        path: 'form-assignments',
        canActivate: [permissionGuard('view_form')],
        loadComponent: () =>
          import('@app/pages/form-assignments/form-assignments').then((m) => m.FormAssignmentsPage),
      },
      {
        path: 'form-fill/:id',
        canActivate: [permissionGuard('fill_form')],
        loadComponent: () =>
          import('@app/pages/form-fill/form-fill').then((m) => m.FormFillPage),
      },
      {
        path: 'gap-analysis',
        canActivate: [permissionGuard('view_gap')],
        loadComponent: () =>
          import('@app/pages/gap-analysis/gap-analysis').then((m) => m.GapAnalysisPage),
      },
      {
        path: 'gap-dashboard',
        canActivate: [permissionGuard('view_gap')],
        loadComponent: () =>
          import('@app/pages/gap-dashboard/gap-dashboard').then((m) => m.GapDashboardPage),
      },
      {
        path: 'gap-catalog',
        canActivate: [permissionGuard('view_gap')],
        loadComponent: () =>
          import('@app/pages/gap-catalog/gap-catalog').then((m) => m.GapCatalogPage),
      },
      {
        path: 'gap-baselines',
        canActivate: [permissionGuard('view_gap')],
        loadComponent: () =>
          import('@app/pages/gap-baselines/gap-baselines').then((m) => m.GapBaselinesPage),
      },
      {
        path: 'soa',
        canActivate: [permissionGuard('view_soa')],
        loadComponent: () => import('@app/pages/soa/soa').then((m) => m.SoaPage),
      },
      {
        path: 'soa-versions',
        canActivate: [permissionGuard('view_soa')],
        loadComponent: () =>
          import('@app/pages/soa-versions/soa-versions').then((m) => m.SoaVersionsPage),
      },
    ],
  },
  {
    path: 'respond/:token',
    loadComponent: () =>
      import('@app/pages/form-respond/form-respond').then((m) => m.FormRespondPage),
  },
  { path: '', pathMatch: 'full', redirectTo: 'app' },
  { path: '**', redirectTo: 'app' },
];
