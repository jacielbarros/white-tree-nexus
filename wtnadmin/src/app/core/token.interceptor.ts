import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthStore } from '@app/core/auth.store';

/** Injeta `Authorization: Bearer` + `X-Org-Context`; em 401 de sessão expirada, limpa e redireciona. */
export const tokenInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(AuthStore);
  const router = inject(Router);

  const token = store.token();
  const orgId = store.activeOrgId();

  let headers = req.headers;
  if (token) {
    headers = headers.set('Authorization', `Bearer ${token}`);
  }
  if (orgId) {
    headers = headers.set('X-Org-Context', orgId);
  }

  return next(req.clone({ headers })).pipe(
    catchError((err: HttpErrorResponse) => {
      // Só desloga se havia sessão (evita interferir no 401 de login/credencial inválida).
      if (err.status === 401 && token) {
        store.clear();
        void router.navigateByUrl('/login');
      }
      return throwError(() => err);
    }),
  );
};
