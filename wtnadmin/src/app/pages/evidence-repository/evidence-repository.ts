import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { Classification, EvidenceSummary, SgsiArtifactType } from '@app/core/models';

const ARTIFACT_LABELS: Record<SgsiArtifactType, string> = {
  soa_item: 'Controle SoA',
  gap_item: 'Item do Gap',
  risk: 'Risco',
  asset: 'Ativo',
  audit_finding: 'Constatação',
};

const CLASSIFICATION_LABELS: Record<Classification, string> = {
  publico: 'Público',
  uso_interno: 'Uso interno',
  confidencial: 'Confidencial',
  restrito: 'Restrito',
};

/** Repositório central de evidências (Feature 014, US2): pesquisa/filtra todas as evidências do tenant. */
@Component({
  selector: 'app-evidence-repository',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ButtonModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Repositório de Evidências</h1>
        <p class="wtn-page-desc">Evidências de conformidade de toda a organização, pesquisáveis e filtráveis.</p>
      </div>
      <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
    </header>

    <section class="filters">
      <input type="text" [(ngModel)]="q" (keyup.enter)="load()" placeholder="Buscar por título…" />
      <select [(ngModel)]="targetType">
        <option value="">Todos os artefatos</option>
        <option value="soa_item">Controle SoA</option>
        <option value="gap_item">Item do Gap</option>
        <option value="risk">Risco</option>
        <option value="asset">Ativo</option>
        <option value="audit_finding">Constatação</option>
      </select>
      <select [(ngModel)]="classification">
        <option value="">Todas as classificações</option>
        <option value="publico">Público</option>
        <option value="uso_interno">Uso interno</option>
        <option value="confidencial">Confidencial</option>
        <option value="restrito">Restrito</option>
      </select>
      @if (canManage()) {
        <select [(ngModel)]="status">
          <option value="">Ativas</option>
          <option value="inactive">Inativas</option>
        </select>
      }
      <button type="button" class="filters__btn" (click)="load()">Filtrar</button>
    </section>

    @if (loading()) {
      <div class="wtn-card pad muted">Carregando evidências…</div>
    } @else if (!items().length) {
      <div class="wtn-empty"><div class="wtn-empty-title">Nenhuma evidência encontrada</div></div>
    } @else {
      <div class="list">
        @for (ev of items(); track ev.id) {
          <article class="row">
            <div class="row__main">
              <strong>{{ ev.title }}</strong>
              <div class="chips">
                <span class="chip chip--cls">{{ classificationLabel(ev.classification) }}</span>
                @for (l of ev.links; track l.id) {
                  <span class="chip">{{ artifactLabel(l.target_type) }}</span>
                }
                @if (ev.status === 'inactive') { <span class="chip chip--off">Inativa</span> }
              </div>
              <small>{{ ev.extension }} · {{ formatSize(ev.size_bytes) }} · {{ ev.hash_algorithm }}:{{ shortHash(ev.content_hash) }} · {{ formatDate(ev.uploaded_at) }}</small>
            </div>
            <div class="row__actions">
              @if (ev.can_download) {
                <button type="button" (click)="download(ev)" title="Baixar"><span class="pi pi-download"></span></button>
              } @else {
                <button type="button" disabled title="Conteúdo restrito pela classificação"><span class="pi pi-lock"></span></button>
              }
            </div>
          </article>
        }
      </div>
    }
  `,
  styles: `
    :host { display: block; }
    .filters { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    .filters input[type=text], .filters select { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 7px 10px; }
    .filters input[type=text] { min-width: 240px; }
    .filters__btn { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 7px 16px; }
    .muted { color: var(--wtn-text-2); }
    .list { display: grid; gap: 8px; }
    .row { align-items: center; background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); box-shadow: var(--wtn-e1); display: flex; gap: 12px; justify-content: space-between; padding: 12px 14px; }
    .row__main { display: grid; gap: 4px; }
    .row__main strong { color: var(--wtn-text); font-size: 13.5px; }
    .row__main small { color: var(--wtn-text-2); font-size: 11.5px; }
    .chips { display: flex; flex-wrap: wrap; gap: 5px; }
    .chip { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: 999px; color: var(--wtn-text-2); font-size: 10.5px; padding: 2px 9px; }
    .chip--cls { border-color: var(--wtn-primary); color: var(--wtn-primary); }
    .chip--off { border-color: var(--wtn-border-strong); color: var(--wtn-muted); }
    .row__actions button { align-items: center; background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text-2); cursor: pointer; display: flex; height: 32px; justify-content: center; width: 32px; }
    .row__actions button:hover:not(:disabled) { border-color: var(--wtn-border-strong); color: var(--wtn-primary); }
    .row__actions button:disabled { opacity: .5; cursor: not-allowed; }
  `,
})
export class EvidenceRepositoryPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly store = inject(AuthStore);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(false);
  protected readonly items = signal<EvidenceSummary[]>([]);
  protected q = '';
  protected targetType: SgsiArtifactType | '' = '';
  protected classification: Classification | '' = '';
  protected status: 'inactive' | '' = '';

  ngOnInit(): void {
    this.load();
  }

  protected canManage(): boolean {
    return hasPermission(this.store.currentRole(), 'manage_evidence');
  }

  protected load(): void {
    const params: Record<string, string> = {};
    if (this.q.trim()) params['q'] = this.q.trim();
    if (this.targetType) params['target_type'] = this.targetType;
    if (this.classification) params['classification'] = this.classification;
    if (this.status) params['status'] = this.status;
    this.loading.set(true);
    this.api.listEvidence(params).subscribe({
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

  protected download(ev: EvidenceSummary): void {
    this.api.downloadEvidence(ev.id).subscribe({
      next: (blob) => this.downloadBlob(blob, ev.file_name),
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro ao baixar', detail: this.errorDetail(e) }),
    });
  }

  protected artifactLabel(t: SgsiArtifactType): string {
    return ARTIFACT_LABELS[t];
  }

  protected classificationLabel(c: Classification): string {
    return CLASSIFICATION_LABELS[c];
  }

  protected shortHash(value: string): string {
    return value.slice(0, 12);
  }

  protected formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  }

  private downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  private errorDetail(error: unknown): string {
    if (typeof error === 'object' && error && 'error' in error) {
      const payload = (error as { error?: { detail?: string } }).error;
      if (payload?.detail) return payload.detail;
    }
    if (typeof error === 'object' && error && 'message' in error) {
      return String((error as { message?: unknown }).message);
    }
    return 'Operação não concluída.';
  }
}
