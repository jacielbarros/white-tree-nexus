import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';

/** Exige sessão autenticada. */
export const authGuard: CanActivateFn = () => {
  const store = inject(AuthStore);
  const router = inject(Router);
  return store.isAuthenticated() ? true : router.createUrlTree(['/login']);
};

/** Exige uma permissão (papel) na organização ativa. */
export function permissionGuard(permission: string): CanActivateFn {
  return () => {
    const store = inject(AuthStore);
    const router = inject(Router);
    if (!store.isAuthenticated()) {
      return router.createUrlTree(['/login']);
    }
    return hasPermission(store.currentRole(), permission) ? true : router.createUrlTree(['/app']);
  };
}

/** Exige Super Admin da plataforma (conteúdo de plataforma, ex.: orientação do Gap). */
export const superAdminGuard: CanActivateFn = () => {
  const store = inject(AuthStore);
  const router = inject(Router);
  if (!store.isAuthenticated()) {
    return router.createUrlTree(['/login']);
  }
  return store.isSuperAdmin() ? true : router.createUrlTree(['/app']);
};
