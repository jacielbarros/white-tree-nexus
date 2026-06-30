import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { ManagementReviewDetail, ManagementReviewVersion } from '@app/core/models';

interface KV { key: string; value: string; }

/** Detalhe da ata 9.3: entradas/saídas, revisão, aprovação (assinatura opcional), versões, PDF. */
@Component({
  selector: 'app-management-review-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, ButtonModule],
  template: `
    <a class="back" routerLink="../management-reviews">← Análises críticas</a>

    @if (review(); as r) {
      <header class="wtn-page-header">
        <div>
          <h1 class="wtn-page-title">{{ r.title }}</h1>
          <p class="wtn-page-desc">{{ r.review_date }} · <span class="status">{{ r.draft_status }}</span></p>
        </div>
        @if (r.draft_status === 'draft' && canManage()) {
          <p-button label="Enviar para revisão" severity="secondary" (onClick)="submitReview(r)" [disabled]="!canSubmit()" />
        }
      </header>

      <div class="grid">
        <section class="wtn-card pad">
          <div class="wtn-card-title">Entradas (9.3.2)</div>
          @for (kv of inputs(); track $index) {
            <div class="kv">
              <input type="text" [(ngModel)]="kv.key" name="ik-{{ $index }}" placeholder="Tópico" [disabled]="!editable()" />
              <input type="text" [(ngModel)]="kv.value" name="iv-{{ $index }}" placeholder="Conteúdo" [disabled]="!editable()" />
              @if (editable()) { <button type="button" class="x" (click)="removeInput($index)">×</button> }
            </div>
          }
          @if (editable()) { <button type="button" class="btn-sec" (click)="addInput()">+ entrada</button> }
        </section>

        <section class="wtn-card pad">
          <div class="wtn-card-title">Saídas (9.3.3)</div>
          @for (kv of outputs(); track $index) {
            <div class="kv">
              <input type="text" [(ngModel)]="kv.key" name="ok-{{ $index }}" placeholder="Decisão" [disabled]="!editable()" />
              <input type="text" [(ngModel)]="kv.value" name="ov-{{ $index }}" placeholder="Detalhe" [disabled]="!editable()" />
              @if (editable()) { <button type="button" class="x" (click)="removeOutput($index)">×</button> }
            </div>
          }
          @if (editable()) { <button type="button" class="btn-sec" (click)="addOutput()">+ saída</button> }
        </section>
      </div>

      @if (editable()) {
        <button type="button" class="btn-primary" (click)="save(r)">Salvar</button>
      }

      <section class="wtn-card pad">
        <div class="wtn-card-title">Aprovação e versões</div>
        @if (r.draft_status === 'in_review' && canApprove()) {
          <form class="inline-form" (submit)="approve(r, $event)">
            <label class="chk"><input type="checkbox" [(ngModel)]="sign" name="sign" /> Assinar (assinatura avançada)</label>
            <select [(ngModel)]="classification" name="cls">
              <option value="uso_interno">Uso interno</option>
              <option value="confidencial">Confidencial</option>
              <option value="restrito">Restrito</option>
              <option value="publico">Público</option>
            </select>
            <button type="submit" class="btn-primary" [disabled]="!r.readiness.can_approve"
              [title]="r.readiness.can_approve ? '' : 'Exige entradas e saídas preenchidas'">Aprovar ata</button>
          </form>
        }
        @if (!versions().length) {
          <p class="muted">Nenhuma versão emitida.</p>
        } @else {
          @for (v of versions(); track v.id) {
            <div class="ver-row">
              <span class="vn">v{{ v.version_number }}</span>
              <span class="status">{{ v.status }}</span>
              @if (v.signed) { <span class="badge">Assinada</span> }
              <button type="button" class="btn-sec" (click)="exportPdf(v)"><span class="pi pi-file-pdf"></span> PDF</button>
            </div>
          }
        }
      </section>
    } @else {
      <p class="muted">Carregando…</p>
    }
  `,
  styles: `
    :host { display: block; }
    .back { color: var(--wtn-primary); display: inline-block; font-size: 12.5px; margin-bottom: 8px; text-decoration: none; }
    .grid { display: grid; gap: 12px; grid-template-columns: 1fr 1fr; margin-bottom: 12px; }
    @media (max-width: 880px) { .grid { grid-template-columns: 1fr; } }
    .kv { align-items: center; display: flex; gap: 6px; margin-bottom: 6px; }
    .kv input:first-child { flex: 0 0 38%; }
    .kv input:nth-child(2) { flex: 1; }
    input, select { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 6px 9px; font: inherit; }
    .x { background: none; border: none; color: #d14343; cursor: pointer; font-size: 16px; }
    .btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; margin: 8px 0; padding: 7px 16px; }
    .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sec { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); cursor: pointer; padding: 5px 12px; }
    .muted { color: var(--wtn-text-2); }
    .inline-form { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 10px; }
    .chk { align-items: center; color: var(--wtn-text-2); display: flex; font-size: 12.5px; gap: 5px; }
    .ver-row { align-items: center; border-top: 1px solid var(--wtn-border); display: flex; gap: 10px; padding: 7px 0; }
    .vn { font-weight: 700; }
    .status { border-radius: 999px; font-size: 10.5px; padding: 2px 9px; border: 1px solid var(--wtn-border); color: var(--wtn-text-2); }
    .badge { background: #2e9e5b; border-radius: 999px; color: #fff; font-size: 10px; padding: 2px 8px; }
  `,
})
export class ManagementReviewDetailPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly route = inject(ActivatedRoute);
  private readonly messages = inject(MessageService);

  protected readonly review = signal<ManagementReviewDetail | null>(null);
  protected readonly versions = signal<ManagementReviewVersion[]>([]);
  protected readonly inputs = signal<KV[]>([]);
  protected readonly outputs = signal<KV[]>([]);

  protected sign = false;
  protected classification = 'uso_interno';

  protected readonly canManage = computed(() => hasPermission(this.store.currentRole(), 'manage_management_review'));
  protected readonly canApprove = computed(() => hasPermission(this.store.currentRole(), 'approve_management_review'));
  protected readonly editable = computed(() => this.canManage() && this.review()?.draft_status === 'draft');

  private get id(): string {
    return this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.api.get<ManagementReviewDetail>(`/management-reviews/${this.id}`).subscribe({
      next: (r) => {
        this.review.set(r);
        this.inputs.set(this.toKv(r.inputs));
        this.outputs.set(this.toKv(r.outputs));
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
    this.api.get<ManagementReviewVersion[]>(`/management-reviews/${this.id}/versions`).subscribe({ next: (v) => this.versions.set(v) });
  }

  private toKv(obj: Record<string, unknown>): KV[] {
    return Object.entries(obj || {}).map(([key, value]) => ({ key, value: String(value) }));
  }

  private toDict(rows: KV[]): Record<string, string> {
    const out: Record<string, string> = {};
    for (const r of rows) {
      if (r.key.trim()) out[r.key.trim()] = r.value;
    }
    return out;
  }

  protected addInput(): void { this.inputs.update((rows) => [...rows, { key: '', value: '' }]); }
  protected removeInput(i: number): void { this.inputs.update((rows) => rows.filter((_, idx) => idx !== i)); }
  protected addOutput(): void { this.outputs.update((rows) => [...rows, { key: '', value: '' }]); }
  protected removeOutput(i: number): void { this.outputs.update((rows) => rows.filter((_, idx) => idx !== i)); }

  protected canSubmit(): boolean {
    return Object.keys(this.toDict(this.inputs())).length > 0 && Object.keys(this.toDict(this.outputs())).length > 0;
  }

  protected save(r: ManagementReviewDetail): void {
    this.api.put(`/management-reviews/${r.id}`, {
      title: r.title,
      review_date: r.review_date,
      inputs: this.toDict(this.inputs()),
      outputs: this.toDict(this.outputs()),
    }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Ata salva' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected submitReview(r: ManagementReviewDetail): void {
    this.api.post(`/management-reviews/${r.id}/submit-review`, {}).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Enviada para revisão' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected approve(r: ManagementReviewDetail, event: Event): void {
    event.preventDefault();
    this.api.post(`/management-reviews/${r.id}/approve`, { sign: this.sign, classification: this.classification }).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Ata aprovada' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: this.errorDetail(e) }),
    });
  }

  protected exportPdf(v: ManagementReviewVersion): void {
    this.api.getBlob(`/management-reviews/${this.id}/versions/${v.id}/export`).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `analise-critica-v${v.version_number}.pdf`;
        link.click();
        URL.revokeObjectURL(url);
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
