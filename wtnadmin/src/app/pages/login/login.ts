import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

@Component({
  selector: 'app-login',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="wtn-auth-shell">
      <!-- Painel da marca -->
      <div class="wtn-auth-brand">
        <div class="wtn-auth-brand-logo">
          <div class="wtn-auth-brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 3 L12 21 M12 8 L7 5.5 M12 8 L17 5.5 M12 13 L6.5 10 M12 13 L17.5 10"
                    stroke="#fff" stroke-width="1.7" stroke-linecap="round"/>
              <circle cx="12" cy="3" r="1.5" fill="#fff"/>
            </svg>
          </div>
          <span class="wtn-auth-brand-name">White Tree Nexus</span>
        </div>
        <div class="wtn-auth-brand-tagline">
          <p class="wtn-auth-brand-headline">
            Gestão de SGSI e compliance ISO/IEC&nbsp;27001.
          </p>
          <p class="wtn-auth-brand-sub">
            Do diagnóstico de contexto à declaração de aplicabilidade, com rastreabilidade e evidências.
          </p>
        </div>
        <div class="wtn-auth-brand-footer">© 2026 · v1.0</div>
      </div>

      <!-- Formulário -->
      <div class="wtn-auth-form-panel">
        <form class="wtn-auth-form" [formGroup]="form" (ngSubmit)="submit()">
          <h2 class="wtn-auth-form-title">Entrar na plataforma</h2>
          <p class="wtn-auth-form-sub">Acesse com seu e-mail corporativo.</p>

          <div class="wtn-field">
            <label class="wtn-label" for="email">E-mail</label>
            <input
              id="email"
              type="email"
              class="wtn-input"
              formControlName="email"
              autocomplete="username"
              placeholder="voce@empresa.com.br"
            />
          </div>

          <div class="wtn-field">
            <div class="wtn-label-row">
              <label class="wtn-label" for="password">Senha</label>
              <a routerLink="/forgot" class="wtn-link-small">Esqueci a senha</a>
            </div>
            <input
              id="password"
              type="password"
              class="wtn-input"
              formControlName="password"
              autocomplete="current-password"
            />
          </div>

          @if (error()) {
            <div class="wtn-error-msg">{{ error() }}</div>
          }

          <button type="submit" class="wtn-btn-primary wtn-btn-full" [disabled]="loading()">
            @if (loading()) { Entrando… } @else { Entrar }
          </button>

          <p class="wtn-auth-alt">
            Recebeu um convite?
            <a routerLink="/accept" class="wtn-link-small">Ativar conta</a>
          </p>
        </form>
      </div>
    </div>
  `,
  styles: `
    :host { display: block; height: 100vh; }

    .wtn-auth-shell {
      display: flex;
      height: 100%;
      background: var(--wtn-bg);
    }

    /* ── Painel de marca ── */
    .wtn-auth-brand {
      width: 280px;
      flex: none;
      background: var(--wtn-primary);
      padding: 36px 32px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .wtn-auth-brand-logo {
      display: flex; align-items: center; gap: 12px;
    }
    .wtn-auth-brand-icon {
      width: 36px; height: 36px;
      border-radius: 9px;
      background: rgba(255, 255, 255, .18);
      display: flex; align-items: center; justify-content: center;
      flex: none;
    }
    .wtn-auth-brand-name {
      font-size: 15px; font-weight: 700;
      color: #fff;
    }

    .wtn-auth-brand-tagline {}
    .wtn-auth-brand-headline {
      font-size: 20px; font-weight: 600;
      color: #fff;
      line-height: 1.35; letter-spacing: -.01em;
      margin: 0 0 12px;
    }
    .wtn-auth-brand-sub {
      font-size: 12.5px;
      color: rgba(255, 255, 255, .7);
      line-height: 1.55;
      margin: 0;
    }

    .wtn-auth-brand-footer {
      font-family: var(--wtn-font-mono);
      font-size: 10.5px;
      color: rgba(255, 255, 255, .5);
    }

    /* ── Painel do formulário ── */
    .wtn-auth-form-panel {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px;
    }

    .wtn-auth-form {
      width: 100%;
      max-width: 320px;
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .wtn-auth-form-title {
      font-size: 22px; font-weight: 700;
      color: var(--wtn-text);
      margin: 0 0 2px;
      letter-spacing: -.01em;
    }
    .wtn-auth-form-sub {
      font-size: 13px; color: var(--wtn-text-2);
      margin: 0;
    }

    .wtn-field { display: flex; flex-direction: column; gap: 6px; }

    .wtn-label {
      font-size: 12.5px; font-weight: 500;
      color: var(--wtn-text-2);
    }
    .wtn-label-row {
      display: flex; justify-content: space-between; align-items: center;
    }

    .wtn-input {
      font-family: var(--wtn-font-sans);
      width: 100%;
      padding: 10px 12px;
      font-size: 13.5px;
      color: var(--wtn-text);
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      outline: none;
      transition: border-color .15s, box-shadow .15s;

      &:focus {
        border-color: var(--wtn-focus);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--wtn-focus) 26%, transparent);
      }
    }

    .wtn-link-small {
      font-size: 12px; font-weight: 600;
      color: var(--wtn-primary); text-decoration: none;
      &:hover { text-decoration: underline; }
    }

    .wtn-error-msg {
      padding: 10px 12px;
      background: var(--wtn-danger-soft);
      color: var(--wtn-danger);
      border-radius: var(--wtn-r-md);
      font-size: 13px;
      border-left: 3px solid var(--wtn-danger);
    }

    .wtn-btn-primary {
      font-family: var(--wtn-font-sans);
      font-size: 14px; font-weight: 600;
      padding: 11px;
      border-radius: var(--wtn-r-md);
      border: none;
      background: var(--wtn-primary);
      color: var(--wtn-primary-contrast);
      cursor: pointer;
      transition: background .15s;
      &:hover:not(:disabled) { background: var(--wtn-primary-hover); }
      &:disabled { opacity: .5; cursor: not-allowed; }
    }
    .wtn-btn-full { width: 100%; }

    .wtn-auth-alt {
      text-align: center;
      font-size: 12.5px;
      color: var(--wtn-text-2);
      margin: 0;
    }
  `,
})
export class Login {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly router = inject(Router);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = this.fb.group({
    email: this.fb.control('', [Validators.required, Validators.email]),
    password: this.fb.control('', Validators.required),
  });

  protected submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.loading.set(true);
    this.error.set(null);
    const { email, password } = this.form.getRawValue();

    this.api.login(email, password).subscribe({
      next: (res) => {
        this.store.setToken(res.access_token);
        this.api.me().subscribe({
          next: (me) => {
            this.store.setMe(me);
            this.loading.set(false);
            void this.router.navigateByUrl('/app');
          },
          error: () => { this.loading.set(false); this.error.set('Não foi possível carregar o perfil.'); },
        });
      },
      error: () => { this.loading.set(false); this.error.set('Credenciais inválidas.'); },
    });
  }
}
