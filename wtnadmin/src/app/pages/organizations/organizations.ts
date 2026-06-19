import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { Organization } from '@app/core/models';

@Component({
  selector: 'app-organizations',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    CardModule,
    TableModule,
    TagModule,
    ButtonModule,
    InputTextModule,
    MessageModule,
  ],
  template: `
    <h2>Organizações</h2>

    @if (isSuperAdmin) {
      <p-card header="Nova organização" styleClass="mb">
        <form [formGroup]="form" (ngSubmit)="create()" class="row-form">
          <input pInputText placeholder="Nome" formControlName="name" />
          <input pInputText placeholder="slug (a-z0-9-)" formControlName="slug" />
          <p-button type="submit" label="Criar" [disabled]="creating()" />
        </form>
        @if (error()) {
          <p-message severity="error" [text]="error()!" />
        }
      </p-card>
    }

    <p-table [value]="orgs()" [loading]="loading()">
      <ng-template pTemplate="header">
        <tr>
          <th>Nome</th>
          <th>Slug</th>
          <th>Status</th>
          @if (isSuperAdmin) {
            <th>Ações</th>
          }
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-org>
        <tr>
          <td>{{ org.name }}</td>
          <td>{{ org.slug }}</td>
          <td>
            <p-tag
              [value]="org.status"
              [severity]="org.status === 'active' ? 'success' : 'danger'"
            />
          </td>
          @if (isSuperAdmin) {
            <td>
              @if (org.status === 'active') {
                <p-button label="Suspender" severity="warn" size="small" (onClick)="setStatus(org, 'suspend')" />
              } @else {
                <p-button label="Reativar" severity="success" size="small" (onClick)="setStatus(org, 'reactivate')" />
              }
            </td>
          }
        </tr>
      </ng-template>
      <ng-template pTemplate="emptymessage">
        <tr><td colspan="4">Nenhuma organização.</td></tr>
      </ng-template>
    </p-table>
  `,
  styles: `
    .row-form { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    .mb { display: block; margin-bottom: 1.25rem; }
    h2 { margin-top: 0; }
  `,
})
export class Organizations implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly store = inject(AuthStore);

  protected readonly isSuperAdmin = this.store.isSuperAdmin();
  protected readonly orgs = signal<Organization[]>([]);
  protected readonly loading = signal(false);
  protected readonly creating = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = this.fb.group({
    name: this.fb.control('', [Validators.required]),
    slug: this.fb.control('', [Validators.required, Validators.pattern(/^[a-z0-9-]+$/)]),
  });

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.api.listOrganizations().subscribe({
      next: (orgs) => {
        this.orgs.set(orgs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  protected create(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.creating.set(true);
    this.error.set(null);
    const { name, slug } = this.form.getRawValue();
    this.api.createOrganization(name, slug).subscribe({
      next: () => {
        this.creating.set(false);
        this.form.reset();
        this.load();
      },
      error: (err: { status?: number }) => {
        this.creating.set(false);
        this.error.set(
          err.status === 409 ? 'Já existe organização com esse slug.' : 'Não foi possível criar.',
        );
      },
    });
  }

  protected setStatus(org: Organization, action: 'suspend' | 'reactivate'): void {
    this.api.changeOrgStatus(org.id, action).subscribe({ next: () => this.load() });
  }
}
