import { DOCUMENT } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SelectModule } from 'primeng/select';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';

interface OrgOption { label: string; value: string; }

@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, FormsModule, SelectModule],
  template: `
    <div class="wtn-layout" [class.wtn-sidebar-collapsed]="collapsed()">

      <!-- ── TOPBAR ── -->
      <header class="wtn-topbar">
        <div class="wtn-topbar-brand">
          <div class="wtn-brand-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M12 3 L12 21 M12 8 L7 5.5 M12 8 L17 5.5 M12 13 L6.5 10 M12 13 L17.5 10"
                    stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
              <circle cx="12" cy="3" r="1.5" fill="currentColor"/>
            </svg>
          </div>
          @if (!collapsed()) {
            <span class="wtn-brand-name">White Tree Nexus</span>
          }
        </div>

        <button class="wtn-icon-btn wtn-sidebar-toggle" (click)="toggleSidebar()" title="Alternar sidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>

        @if (orgOptions().length) {
          <div class="wtn-org-selector">
            <p-select
              [options]="orgOptions()"
              optionLabel="label"
              optionValue="value"
              [ngModel]="store.activeOrgId()"
              (ngModelChange)="onOrgChange($event)"
              placeholder="Selecione organização"
              styleClass="wtn-org-select"
            />
          </div>
        }

        <div class="wtn-topbar-spacer"></div>

        <button class="wtn-icon-btn" (click)="toggleTheme()" [title]="dark() ? 'Tema claro' : 'Tema escuro'">
          @if (dark()) {
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.7"/>
              <path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"
                    stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          } @else {
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
                    stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          }
        </button>

        <div class="wtn-user-avatar" [title]="store.me()?.email ?? ''">
          {{ initials() }}
        </div>

        <button class="wtn-logout-btn" (click)="logout()" title="Sair">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"
                  stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </header>

      <!-- ── BODY (sidebar + main) ── -->
      <div class="wtn-body">
        <nav class="wtn-sidebar">
          <!-- Início -->
          <div class="wtn-nav-group">
            @if (!collapsed()) { <div class="wtn-nav-label">Início</div> }
            <a class="wtn-nav-item" routerLink="dashboard" routerLinkActive="active" [title]="collapsed() ? 'Dashboard' : ''">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M3 11l9-7 9 7M5 10v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9"
                      stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              @if (!collapsed()) { <span>Dashboard de Conformidade</span> }
            </a>
          </div>

          <!-- Administração -->
          <div class="wtn-nav-group">
            @if (!collapsed()) { <div class="wtn-nav-label">Administração</div> }
            <a class="wtn-nav-item" routerLink="organizations" routerLinkActive="active" [title]="collapsed() ? 'Organizações' : ''">
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                <path d="M4 21V7l8-4 8 4v14M9 21v-6h6v6M9 9h.01M15 9h.01M9 12h.01M15 12h.01"
                      stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              @if (!collapsed()) { <span>Organizações</span> }
            </a>
            @if (store.activeOrgId()) {
              <a class="wtn-nav-item" routerLink="users" routerLinkActive="active" [title]="collapsed() ? 'Usuários' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M16 19v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1M9 10a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M22 19v-1a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Usuários</span> }
              </a>
            }
          </div>

          @if (store.activeOrgId()) {
            <!-- Contexto · Cláusula 4 -->
            <div class="wtn-nav-group">
              @if (!collapsed()) { <div class="wtn-nav-label">Contexto · Cláusula 4</div> }
              <a class="wtn-nav-item" routerLink="diagnostic" routerLinkActive="active" [title]="collapsed() ? 'Diagnóstico' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2M9 14l2 2 4-4"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Diagnóstico</span> }
              </a>
              <a class="wtn-nav-item" routerLink="context-analysis" routerLinkActive="active" [title]="collapsed() ? 'Análise de Contexto' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2 2 7l10 5 10-5-10-5M2 17l10 5 10-5M2 12l10 5 10-5"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Análise de Contexto</span> }
              </a>
              <a class="wtn-nav-item" routerLink="stakeholders" routerLinkActive="active" [title]="collapsed() ? 'Partes Interessadas' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/>
                  <circle cx="12" cy="12" r="4.5" stroke="currentColor" stroke-width="1.6"/>
                  <circle cx="12" cy="12" r="1" fill="currentColor"/>
                </svg>
                @if (!collapsed()) { <span>Partes Interessadas</span> }
              </a>
              <a class="wtn-nav-item" routerLink="scope" routerLinkActive="active" [title]="collapsed() ? 'Declaração de Escopo' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M6 2v14a2 2 0 0 0 2 2h14M18 22V8a2 2 0 0 0-2-2H2"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Declaração de Escopo</span> }
              </a>
              <a class="wtn-nav-item" routerLink="context-overview" routerLinkActive="active" [title]="collapsed() ? 'Visão Consolidada' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="12" cy="12" r="2.5" stroke="currentColor" stroke-width="1.6"/>
                </svg>
                @if (!collapsed()) { <span>Visão Consolidada</span> }
              </a>
            </div>

            <!-- Workflow -->
            <div class="wtn-nav-group">
              @if (!collapsed()) { <div class="wtn-nav-label">Workflow</div> }
              <a class="wtn-nav-item" routerLink="form-templates" routerLinkActive="active" [title]="collapsed() ? 'Templates' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="1.6"/>
                  <path d="M3 9h18M9 21V9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                </svg>
                @if (!collapsed()) { <span>Templates</span> }
              </a>
              <a class="wtn-nav-item" routerLink="form-assignments" routerLinkActive="active" [title]="collapsed() ? 'Formulários' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M9 11l3 3L22 4M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Formulários</span> }
              </a>
              @if (canManagePrintTemplates()) {
                <a class="wtn-nav-item" routerLink="print-templates" routerLinkActive="active" [title]="collapsed() ? 'Templates de impressão' : ''">
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                    <path d="M7 3h8l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"
                          stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M15 3v5h5M9 13h6M9 17h4"
                          stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  @if (!collapsed()) { <span>Templates de impressão</span> }
                </a>
              }
            </div>

            <!-- Gap Analysis -->
            <div class="wtn-nav-group">
              @if (!collapsed()) { <div class="wtn-nav-label">Gap Analysis</div> }
              <a class="wtn-nav-item" routerLink="gap-analysis" routerLinkActive="active" [title]="collapsed() ? 'Matriz' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.6"/>
                  <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.6"/>
                  <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.6"/>
                  <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" stroke-width="1.6"/>
                </svg>
                @if (!collapsed()) { <span>Matriz</span> }
              </a>
              <a class="wtn-nav-item" routerLink="gap-dashboard" routerLinkActive="active" [title]="collapsed() ? 'Dashboard Gap' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M3 3v18h18M7 14l3-3 3 3 5-6"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Dashboard</span> }
              </a>
              <a class="wtn-nav-item" routerLink="gap-catalog" routerLinkActive="active" [title]="collapsed() ? 'Catálogo' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15z"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Catálogo</span> }
              </a>
              <a class="wtn-nav-item" routerLink="gap-baselines" routerLinkActive="active" [title]="collapsed() ? 'Baselines' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M4 22V4a2 2 0 0 1 2-2h9l1 2h4v9h-5l-1-2H6a2 2 0 0 0-2 2"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Baselines</span> }
              </a>
              @if (store.isSuperAdmin()) {
                <a class="wtn-nav-item" routerLink="gap-guidance-admin" routerLinkActive="active" [title]="collapsed() ? 'Orientação (admin)' : ''">
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                    <path d="M12 2v2m0 16v2m10-10h-2M4 12H2m15.5-6.5-1.5 1.5M6 18l1.5-1.5m11 1.5L17 16.5M6 6l1.5 1.5"
                          stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                    <circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="1.6"/>
                  </svg>
                  @if (!collapsed()) { <span>Orientação (admin)</span> }
                </a>
              }
            </div>

            <!-- Ativos e Processos -->
            <div class="wtn-nav-group">
              @if (!collapsed()) { <div class="wtn-nav-label">Ativos e Processos</div> }
              <a class="wtn-nav-item" routerLink="assets" routerLinkActive="active" [title]="collapsed() ? 'Inventário' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M3.3 7 12 12l8.7-5M12 22V12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Inventário</span> }
              </a>
              <a class="wtn-nav-item" routerLink="assets-dashboard" routerLinkActive="active" [title]="collapsed() ? 'Dashboard Ativos' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M3 3v18h18M7 14l3-3 3 3 5-6"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Dashboard</span> }
              </a>
            </div>

            <!-- SoA -->
            <div class="wtn-nav-group">
              @if (!collapsed()) { <div class="wtn-nav-label">SoA</div> }
              <a class="wtn-nav-item" routerLink="soa" routerLinkActive="active" [title]="collapsed() ? 'Aplicabilidade' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2 4 5v6c0 5 3.4 8.5 8 11 4.6-2.5 8-6 8-11V5l-8-3M9 12l2 2 4-4"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Aplicabilidade</span> }
              </a>
              <a class="wtn-nav-item" routerLink="soa-versions" routerLinkActive="active" [title]="collapsed() ? 'Versões SoA' : ''">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
                  <path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"
                        stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                @if (!collapsed()) { <span>Versões</span> }
              </a>
            </div>
          }
        </nav>

        <main class="wtn-main">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: `
    :host { display: contents; }

    .wtn-layout {
      display: flex;
      flex-direction: column;
      height: 100vh;
      background: var(--wtn-bg);
    }

    /* ── TOPBAR ── */
    .wtn-topbar {
      height: 56px;
      flex: none;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 16px;
      background: var(--wtn-surface);
      border-bottom: 1px solid var(--wtn-border);
      z-index: 10;
    }

    .wtn-topbar-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 214px;
      flex: none;
      overflow: hidden;
      transition: width .2s;
    }
    .wtn-sidebar-collapsed .wtn-topbar-brand { width: 40px; }

    .wtn-brand-icon {
      width: 30px; height: 30px;
      border-radius: 8px;
      background: var(--wtn-primary);
      color: var(--wtn-primary-contrast);
      display: flex; align-items: center; justify-content: center;
      flex: none;
    }
    .wtn-brand-name {
      font-size: 14.5px;
      font-weight: 700;
      letter-spacing: -.01em;
      color: var(--wtn-text);
      white-space: nowrap;
    }

    .wtn-sidebar-toggle {
      margin-left: -4px;
    }

    .wtn-org-selector {
      max-width: 220px;
    }
    ::ng-deep .wtn-org-select .p-select {
      border-color: var(--wtn-border-strong);
      background: var(--wtn-surface);
      border-radius: var(--wtn-r-md);
      font-size: 13px;
    }

    .wtn-topbar-spacer { flex: 1; }

    .wtn-icon-btn {
      width: 34px; height: 34px;
      border-radius: var(--wtn-r-md);
      border: 1px solid var(--wtn-border);
      background: var(--wtn-surface);
      color: var(--wtn-text-2);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer;
      transition: background .15s, color .15s;
      &:hover { background: var(--wtn-surface-2); color: var(--wtn-text); }
    }

    .wtn-user-avatar {
      width: 32px; height: 32px;
      border-radius: 50%;
      background: var(--wtn-primary);
      color: var(--wtn-primary-contrast);
      display: flex; align-items: center; justify-content: center;
      font-size: 11.5px;
      font-weight: 700;
      cursor: default;
    }

    .wtn-logout-btn {
      width: 32px; height: 32px;
      border-radius: var(--wtn-r-md);
      border: none;
      background: transparent;
      color: var(--wtn-muted);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer;
      transition: color .15s;
      &:hover { color: var(--wtn-danger); }
    }

    /* ── BODY ── */
    .wtn-body {
      display: flex;
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }

    /* ── SIDEBAR ── */
    .wtn-sidebar {
      width: 230px;
      flex: none;
      background: var(--wtn-surface);
      border-right: 1px solid var(--wtn-border);
      padding: 12px 10px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      overflow-y: auto;
      transition: width .2s;
    }
    .wtn-sidebar-collapsed .wtn-sidebar { width: 56px; padding: 10px 8px; }

    .wtn-nav-group { display: flex; flex-direction: column; gap: 2px; }

    .wtn-nav-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: .1em;
      text-transform: uppercase;
      color: var(--wtn-muted);
      padding: 0 8px;
      margin-bottom: 4px;
    }

    .wtn-nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 9px;
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text-2);
      font-size: 13px;
      font-weight: 500;
      text-decoration: none;
      cursor: pointer;
      white-space: nowrap;
      overflow: hidden;
      transition: background .12s, color .12s;

      svg { flex: none; }

      &:hover { background: var(--wtn-surface-2); color: var(--wtn-text); }
      &.active { background: var(--wtn-primary-soft); color: var(--wtn-primary); font-weight: 600; }
    }

    /* ── MAIN ── */
    .wtn-main {
      flex: 1;
      min-width: 0;
      overflow-y: auto;
      padding: 24px 28px 32px;
      background: var(--wtn-bg);
    }
  `,
})
export class Shell implements OnInit {
  protected readonly store = inject(AuthStore);
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly doc = inject(DOCUMENT);

  protected readonly orgOptions = signal<OrgOption[]>([]);
  protected readonly collapsed = signal(false);
  protected readonly dark = signal(false);

  ngOnInit(): void {
    const storedTheme = localStorage.getItem('wtn-theme');
    if (storedTheme === 'dark') {
      this.dark.set(true);
      this.doc.documentElement.classList.add('wtn-dark');
    }

    if (this.store.me()) {
      this.buildOptions();
    } else if (this.store.token()) {
      this.api.me().subscribe({
        next: (me) => { this.store.setMe(me); this.buildOptions(); },
        error: () => this.logout(),
      });
    }
  }

  private buildOptions(): void {
    const me = this.store.me();
    if (!me) return;
    if (me.is_super_admin) {
      this.api.listOrganizations().subscribe({
        next: (orgs) => this.orgOptions.set(orgs.map((o) => ({ label: `${o.name} (${o.slug})`, value: o.id }))),
        error: () => this.orgOptions.set([]),
      });
    } else {
      this.orgOptions.set(me.memberships.map((m) => ({ label: m.org_name, value: m.tenant_id })));
    }
  }

  protected toggleSidebar(): void {
    this.collapsed.update((v) => !v);
  }

  protected toggleTheme(): void {
    const next = !this.dark();
    this.dark.set(next);
    if (next) {
      this.doc.documentElement.classList.add('wtn-dark');
      localStorage.setItem('wtn-theme', 'dark');
    } else {
      this.doc.documentElement.classList.remove('wtn-dark');
      localStorage.setItem('wtn-theme', 'light');
    }
  }

  protected initials(): string {
    const me = this.store.me();
    if (!me) return '?';
    const name = me.full_name ?? me.email;
    return name
      .split(/[\s@.]/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0].toUpperCase())
      .join('');
  }

  protected onOrgChange(orgId: string): void {
    if (this.store.activeOrgId() === orgId) {
      return;
    }
    this.store.setActiveOrg(orgId);
    void this.router.navigateByUrl(this.router.url);
  }

  protected canManagePrintTemplates(): boolean {
    return hasPermission(this.store.currentRole(), 'manage_print_templates');
  }

  protected logout(): void {
    this.api.logout().subscribe({ next: () => this.finish(), error: () => this.finish() });
  }

  private finish(): void {
    this.store.clear();
    void this.router.navigateByUrl('/login');
  }
}
