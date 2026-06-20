import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Observable } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { PasswordModule } from 'primeng/password';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { TokenResponse } from '@app/core/models';

type State = 'loading' | 'invalid' | 'new' | 'existing';

@Component({
  selector: 'app-invite-accept',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    CardModule,
    ButtonModule,
    InputTextModule,
    PasswordModule,
    MessageModule,
  ],
  template: `
    <div class="centered">
      <p-card header="Aceitar convite" styleClass="auth-card">
        @switch (state()) {
          @case ('loading') {
            <p class="hint">Carregando convite...</p>
          }
          @case ('invalid') {
            <p-message severity="error" text="Convite inválido, expirado ou já utilizado." />
          }
          @case ('existing') {
            <p class="lead">
              Você foi adicionado à organização <strong>{{ orgName() }}</strong>
              como <strong>{{ roleLabel() }}</strong>.
            </p>
            <p class="hint">Você já tem uma conta — sua senha atual continua valendo.</p>
            @if (error()) {
              <p-message severity="error" [text]="error()!" />
            }
            <p-button
              label="Confirmar e entrar"
              [disabled]="loading()"
              (onClick)="acceptExisting()"
              styleClass="w-full"
            />
          }
          @case ('new') {
            <p class="lead">
              Convite para <strong>{{ orgName() }}</strong> como <strong>{{ roleLabel() }}</strong>.
            </p>
            <form [formGroup]="form" (ngSubmit)="submitNew()" class="auth-form">
              <label for="name">Nome completo</label>
              <input pInputText id="name" formControlName="fullName" />

              <label for="password">Defina sua senha (mín. 12 caracteres)</label>
              <p-password inputId="password" formControlName="password" [toggleMask]="true" />

              @if (error()) {
                <p-message severity="error" [text]="error()!" />
              }

              <p-button type="submit" label="Aceitar e entrar" [disabled]="loading()" styleClass="w-full" />
            </form>
          }
        }
      </p-card>
    </div>
  `,
  styles: `
    .centered { display: flex; justify-content: center; padding: 3rem 1rem; }
    .auth-form { display: flex; flex-direction: column; gap: 0.75rem; min-width: 18rem; }
    .auth-card { min-width: 20rem; }
    .lead { margin-top: 0; }
    .hint { opacity: 0.75; font-size: 0.9rem; }
  `,
})
export class InviteAccept implements OnInit {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly state = signal<State>('loading');
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly orgName = signal('');
  protected readonly roleLabel = signal('');
  private token = '';

  protected readonly form = this.fb.group({
    fullName: this.fb.control('', [Validators.required]),
    password: this.fb.control('', [Validators.required, Validators.minLength(12)]),
  });

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token') ?? '';
    if (!this.token) {
      this.state.set('invalid');
      return;
    }
    this.api.lookupInvite(this.token).subscribe({
      next: (info) => {
        this.orgName.set(info.org_name);
        this.roleLabel.set(info.role);
        this.state.set(info.requires_password ? 'new' : 'existing');
      },
      error: () => this.state.set('invalid'),
    });
  }

  protected submitNew(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { fullName, password } = this.form.getRawValue();
    this.finish(this.api.acceptInvite(this.token, fullName, password));
  }

  protected acceptExisting(): void {
    this.finish(this.api.acceptInvite(this.token));
  }

  private finish(req: Observable<TokenResponse>): void {
    this.loading.set(true);
    this.error.set(null);
    req.subscribe({
      next: (res) => {
        this.store.setToken(res.access_token);
        this.api.me().subscribe({
          next: (me) => {
            this.store.setMe(me);
            this.loading.set(false);
            void this.router.navigateByUrl('/app');
          },
          error: () => {
            this.loading.set(false);
            void this.router.navigateByUrl('/login');
          },
        });
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Convite inválido, expirado ou já utilizado.');
      },
    });
  }
}
