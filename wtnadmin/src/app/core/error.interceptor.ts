import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { MessageService } from 'primeng/api';
import { catchError, throwError } from 'rxjs';

/**
 * Mostra um toast para erros HTTP e repropaga o erro.
 * 401 é ignorado aqui — o `tokenInterceptor` cuida (redireciona p/ login ou a tela trata inline).
 */
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const messages = inject(MessageService);

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status !== 401) {
        messages.add({
          severity: err.status === 0 || err.status >= 500 ? 'error' : 'warn',
          summary: err.status === 0 ? 'Sem conexão' : `Erro ${err.status}`,
          detail: detailFor(err),
          life: 6000,
        });
      }
      return throwError(() => err);
    }),
  );
};

/** Prioriza a mensagem `detail` do backend (FastAPI); senão, texto amigável por status. */
function detailFor(err: HttpErrorResponse): string {
  if (err.status === 0) {
    return 'Não foi possível conectar ao servidor. Verifique se o backend está no ar.';
  }
  const backendDetail =
    err.error && typeof err.error === 'object' ? (err.error as { detail?: unknown }).detail : undefined;
  if (typeof backendDetail === 'string' && backendDetail.trim()) {
    return backendDetail;
  }
  if (err.status >= 500) return 'Erro interno do servidor.';
  if (err.status === 403) return 'Você não tem permissão para esta ação.';
  if (err.status === 404) return 'Recurso não encontrado.';
  return err.message || 'Ocorreu um erro inesperado.';
}
