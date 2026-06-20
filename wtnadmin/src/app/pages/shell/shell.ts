import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';

interface OrgOption {
  label: string;
  value: string;
}

@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, SelectModule, ButtonModule],
  template: `
    <header class="topbar">
      <span class="brand">White Tree Nexus</span>
      <nav>
        <a routerLink="organizations" routerLinkActive="active">Organizações</a>
        @if (store.activeOrgId()) {
          <a routerLink="users" routerLinkActive="active">Usuários</a>
          <a routerLink="diagnostic" routerLinkActive="active">Diagnóstico</a>
          <a routerLink="context-analysis" routerLinkActive="active">Contexto</a>
          <a routerLink="stakeholders" routerLinkActive="active">Partes</a>
          <a routerLink="scope" routerLinkActive="active">Escopo</a>
          <a routerLink="context-overview" routerLinkActive="active">Visão</a>
          <a routerLink="form-templates" routerLinkActive="active">Templates</a>
          <a routerLink="form-assignments" routerLinkActive="active">Formulários</a>
        }
      </nav>
      <span class="spacer"></span>
      @if (orgOptions().length) {
        <p-select
          [options]="orgOptions()"
          optionLabel="label"
          optionValue="value"
          [ngModel]="store.activeOrgId()"
          (ngModelChange)="onOrgChange($event)"
          placeholder="Selecione a organização"
        />
      }
      <span class="email">{{ store.me()?.email }}</span>
      <p-button label="Sair" severity="secondary" (onClick)="logout()" />
    </header>
    <main class="content">
      <router-outlet />
    </main>
  `,
  styles: `
    .topbar {
      display: flex; align-items: center; gap: 1rem;
      padding: 0.75rem 1.25rem; border-bottom: 1px solid var(--p-content-border-color, #ddd);
    }
    .brand { font-weight: 600; }
    nav { display: flex; gap: 1rem; }
    nav a.active { font-weight: 600; text-decoration: underline; }
    .spacer { flex: 1; }
    .email { font-size: 0.85rem; opacity: 0.8; }
    .content { padding: 1.5rem; }
  `,
})
export class Shell implements OnInit {
  protected readonly store = inject(AuthStore);
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  protected readonly orgOptions = signal<OrgOption[]>([]);

  ngOnInit(): void {
    if (this.store.me()) {
      this.buildOptions();
    } else if (this.store.token()) {
      this.api.me().subscribe({
        next: (me) => {
          this.store.setMe(me);
          this.buildOptions();
        },
        error: () => this.logout(),
      });
    }
  }

  private buildOptions(): void {
    const me = this.store.me();
    if (!me) {
      return;
    }
    if (me.is_super_admin) {
      this.api.listOrganizations().subscribe({
        next: (orgs) =>
          this.orgOptions.set(orgs.map((o) => ({ label: `${o.name} (${o.slug})`, value: o.id }))),
        error: () => this.orgOptions.set([]),
      });
    } else {
      this.orgOptions.set(me.memberships.map((m) => ({ label: m.org_name, value: m.tenant_id })));
    }
  }

  protected onOrgChange(orgId: string): void {
    this.store.setActiveOrg(orgId);
  }

  protected logout(): void {
    this.api.logout().subscribe({
      next: () => this.finishLogout(),
      error: () => this.finishLogout(),
    });
  }

  private finishLogout(): void {
    this.store.clear();
    void this.router.navigateByUrl('/login');
  }
}
