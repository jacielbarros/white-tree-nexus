import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { Invitation, MembershipRow, ROLES, Role } from '@app/core/models';
import { hasPermission } from '@app/core/permissions';

@Component({
  selector: 'app-users',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    FormsModule,
    CardModule,
    TableModule,
    TagModule,
    SelectModule,
    ButtonModule,
    InputTextModule,
    MessageModule,
  ],
  template: `
    <h2>Usuários da organização</h2>

    @if (!store.activeOrgId()) {
      <p-message severity="info" text="Selecione uma organização no topo para gerenciar usuários." />
    } @else {
      @if (canInvite()) {
        <p-card header="Convidar usuário" styleClass="mb">
          <form [formGroup]="inviteForm" (ngSubmit)="invite()" class="row-form">
            <input pInputText placeholder="e-mail" formControlName="email" />
            <p-select [options]="roles" formControlName="role" placeholder="Papel" />
            <p-button type="submit" label="Convidar" [disabled]="inviting()" />
          </form>
          @if (inviteError()) {
            <p-message severity="error" [text]="inviteError()!" />
          }
        </p-card>
      }

      <p-table [value]="users()" [loading]="loading()">
        <ng-template pTemplate="header">
          <tr>
            <th>E-mail</th>
            <th>Nome</th>
            <th>Papel</th>
            <th>Status</th>
            @if (canManage()) {
              <th>Ações</th>
            }
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-row>
          <tr>
            <td>{{ row.email }}</td>
            <td>{{ row.full_name }}</td>
            <td>
              @if (canManage()) {
                <p-select
                  [options]="roles"
                  [ngModel]="row.role"
                  (ngModelChange)="changeRole(row, $event)"
                  appendTo="body"
                />
              } @else {
                {{ row.role }}
              }
            </td>
            <td>
              <p-tag [value]="row.status" [severity]="row.status === 'active' ? 'success' : 'secondary'" />
              @if (row.locked) {
                <p-tag value="bloqueado" severity="danger" />
              }
            </td>
            @if (canManage()) {
              <td>
                @if (row.locked) {
                  <p-button label="Desbloquear" size="small" (onClick)="unlock(row)" />
                }
              </td>
            }
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
          <tr><td colspan="5">Nenhum usuário.</td></tr>
        </ng-template>
      </p-table>

      @if (canInvite()) {
        <h3>Convites</h3>
        <p-table [value]="invitations()">
          <ng-template pTemplate="header">
            <tr><th>E-mail</th><th>Papel</th><th>Status</th><th>Ações</th></tr>
          </ng-template>
          <ng-template pTemplate="body" let-inv>
            <tr>
              <td>{{ inv.email }}</td>
              <td>{{ inv.role }}</td>
              <td><p-tag [value]="inv.status" /></td>
              <td>
                @if (inv.status === 'pending') {
                  <p-button label="Revogar" severity="danger" size="small" (onClick)="revoke(inv)" />
                }
              </td>
            </tr>
          </ng-template>
          <ng-template pTemplate="emptymessage">
            <tr><td colspan="4">Nenhum convite.</td></tr>
          </ng-template>
        </p-table>
      }
    }
  `,
  styles: `
    .row-form { display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    .mb { display: block; margin-bottom: 1.25rem; }
    h2 { margin-top: 0; }
  `,
})
export class Users {
  protected readonly store = inject(AuthStore);
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly roles = ROLES;
  protected readonly users = signal<MembershipRow[]>([]);
  protected readonly invitations = signal<Invitation[]>([]);
  protected readonly loading = signal(false);
  protected readonly inviting = signal(false);
  protected readonly inviteError = signal<string | null>(null);

  protected readonly canManage = computed(() =>
    hasPermission(this.store.currentRole(), 'manage_memberships'),
  );
  protected readonly canInvite = computed(() =>
    hasPermission(this.store.currentRole(), 'invite_users'),
  );

  protected readonly inviteForm = this.fb.group({
    email: this.fb.control('', [Validators.required, Validators.email]),
    role: this.fb.control<Role>('manager', [Validators.required]),
  });

  constructor() {
    // Recarrega ao trocar de organização (X-Org-Context muda no interceptor).
    effect(() => {
      const org = this.store.activeOrgId();
      if (org) {
        this.loadUsers();
        if (this.canInvite()) {
          this.loadInvites();
        }
      }
    });
  }

  private loadUsers(): void {
    this.loading.set(true);
    this.api.listUsers().subscribe({
      next: (rows) => {
        this.users.set(rows);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private loadInvites(): void {
    this.api.listInvitations().subscribe({ next: (rows) => this.invitations.set(rows) });
  }

  protected invite(): void {
    if (this.inviteForm.invalid) {
      this.inviteForm.markAllAsTouched();
      return;
    }
    this.inviting.set(true);
    this.inviteError.set(null);
    const { email, role } = this.inviteForm.getRawValue();
    this.api.createInvitation(email, role).subscribe({
      next: () => {
        this.inviting.set(false);
        this.inviteForm.reset({ email: '', role: 'manager' });
        this.loadInvites();
      },
      error: (err: { status?: number }) => {
        this.inviting.set(false);
        this.inviteError.set(
          err.status === 409 ? 'Já há convite pendente ou vínculo para este e-mail.' : 'Falha ao convidar.',
        );
      },
    });
  }

  protected changeRole(row: MembershipRow, role: Role): void {
    if (role === row.role) {
      return;
    }
    this.api.changeRole(row.id, role).subscribe({
      next: () => this.loadUsers(),
      error: () => this.loadUsers(),
    });
  }

  protected unlock(row: MembershipRow): void {
    this.api.unlockUser(row.user_id).subscribe({ next: () => this.loadUsers() });
  }

  protected revoke(inv: Invitation): void {
    this.api.revokeInvitation(inv.id).subscribe({ next: () => this.loadInvites() });
  }
}
