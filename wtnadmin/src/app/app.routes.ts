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
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'app' },
  { path: '**', redirectTo: 'app' },
];
