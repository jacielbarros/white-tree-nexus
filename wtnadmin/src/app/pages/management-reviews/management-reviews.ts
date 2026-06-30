import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { ManagementReviewSummary } from '@app/core/models';

/** Análise Crítica pela Direção (9.3) — coleção de atas (Feature 015, US5). */
@Component({
  selector: 'app-management-reviews',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Análise Crítica pela Direção</h1>
        <p class="wtn-page-desc">Atas de análise crítica do SGSI (cláusula 9.3) — uma por reunião.</p>
      </div>
      <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
    </header>

    @if (canManage()) {
      <section class="wtn-card pad">
        <div class="wtn-card-title">Nova análise crítica</div>
        <form class="inline-form" (submit)="create($event)">
          <input type="text" [(ngModel)]="newTitle" name="t" placeholder="Título (ex.: Análise Crítica 2026/1)" />
          <input type="date" [(ngModel)]="newDate" name="d" />
          <button type="submit" class="btn-primary" [disabled]="!canCreate()">Criar ata</button>
        </form>
      </section>
    }

    <section class="wtn-card pad">
      <div class="wtn-card-title">Atas</div>
      @if (loading()) {
        <p class="muted">Carregando…</p>
      } @else if (!items().length) {
        <div class="wtn-empty"><div class="wtn-empty-title">Nenhuma análise crítica</div></div>
      } @else {
        <div class="mr-list">
          @for (r of items(); track r.id) {
            <a class="mr-row" [routerLink]="['../management-review-detail', r.id]">
              <span class="title">{{ r.title }}</span>
              <span class="date">{{ r.review_date }}</span>
              <span class="status status--{{ r.draft_status }}">{{ r.draft_status }}</span>
              @if (r.current_version_id) { <span class="badge">Aprovada</span> }
            </a>
          }
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .inline-form { display: flex; flex-wrap: wrap; gap: 8px; }
    input { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 7px 10px; font: inherit; }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .muted { color: var(--wtn-text-2); }
    .mr-list { display: grid; gap: 6px; }
    .mr-row { align-items: center; border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); display: flex; gap: 10px; padding: 9px 12px; text-decoration: none; }
    .mr-row:hover { border-color: var(--wtn-primary); }
    .mr-row .title { flex: 1; font-size: 13px; }
    .mr-row .date { color: var(--wtn-text-2); font-size: 12px; }
    .status { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); }
    .status--in_review { border-color: var(--wtn-primary); color: var(--wtn-primary); }
    .status--in_force { border-color: #2e9e5b; color: #2e9e5b; }
    .badge { background: var(--wtn-primary); border-radius: 999px; color: #fff; font-size: 10px; padding: 2px 8px; }
  `,
})
export class ManagementReviewsPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly items = signal<ManagementReviewSummary[]>([]);

  protected newTitle = '';
  protected newDate = new Date().toISOString().slice(0, 10);

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_management_review'));

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.get<ManagementReviewSummary[]>('/management-reviews').subscribe({
      next: (rows) => {
        this.items.set(rows);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected canCreate(): boolean {
    return !!(this.newTitle.trim() && this.newDate);
  }

  protected create(event: Event): void {
    event.preventDefault();
    if (!this.canCreate()) return;
    this.api.post<ManagementReviewSummary>('/management-reviews', { title: this.newTitle.trim(), review_date: this.newDate }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Ata criada' });
        this.newTitle = '';
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    return 'Operação não concluída.';
  }
}
