import { ChangeDetectionStrategy, Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { Classification, EvidenceHistory, EvidenceSummary, SgsiArtifactType } from '@app/core/models';

/**
 * Painel reutilizável de evidências (Feature 014). Lista, anexa, baixa e inativa evidências
 * vinculadas a um artefato do SGSI (controle SoA / risco / ativo / item Gap / constatação).
 * O backend valida tenant + permissão + classificação; este componente é só a UX.
 */
@Component({
  selector: 'app-evidence-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule, FormsModule],
  template: `
    <section class="ev">
      <div class="ev__head">
        <div>
          <div class="ev__eyebrow">Evidências anexadas</div>
          <strong>{{ title() }}</strong>
        </div>
        <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
      </div>

      @if (canManage()) {
        <form class="ev__upload" (submit)="upload($event)">
          <input type="file" (change)="onFile($event)" [disabled]="uploading()" />
          <select [(ngModel)]="classification" name="classification" [disabled]="uploading()">
            <option value="publico">Público</option>
            <option value="uso_interno">Uso interno</option>
            <option value="confidencial">Confidencial</option>
            <option value="restrito">Restrito</option>
          </select>
          <input type="text" name="title" [(ngModel)]="uploadTitle" placeholder="Título (opcional)" [disabled]="uploading()" />
          <button type="submit" class="ev__btn-primary" [disabled]="!selectedFile() || uploading()">
            {{ uploading() ? 'Enviando…' : 'Anexar' }}
          </button>
        </form>
      }

      @if (loading()) {
        <div class="ev__empty">Carregando evidências…</div>
      } @else if (!items().length) {
        <div class="ev__empty">Nenhuma evidência anexada ainda.</div>
      } @else {
        <div class="ev__list">
          @for (ev of items(); track ev.id) {
            <div class="ev__row">
              <div class="ev__meta">
                <strong>{{ ev.title }}</strong>
                <span>
                  {{ classificationLabel(ev.classification) }} · {{ ev.extension }} · {{ formatSize(ev.size_bytes) }}
                  · {{ formatDate(ev.uploaded_at) }}
                </span>
                <small title="Hash de integridade">{{ ev.hash_algorithm }}:{{ shortHash(ev.content_hash) }}</small>
              </div>
              <div class="ev__actions">
                @if (ev.can_download) {
                  <button type="button" (click)="download(ev)" title="Baixar"><span class="pi pi-download"></span></button>
                } @else {
                  <button type="button" disabled title="Conteúdo restrito pela classificação"><span class="pi pi-lock"></span></button>
                }
                @if (canManage()) {
                  <button type="button" (click)="triggerReplace(ev)" title="Substituir por nova versão"><span class="pi pi-upload"></span></button>
                  <button type="button" (click)="toggleHistory(ev)" title="Histórico de versões"><span class="pi pi-history"></span></button>
                  <button type="button" (click)="inactivate(ev)" title="Inativar"><span class="pi pi-trash"></span></button>
                }
              </div>
            </div>
            @if (historyOf() === ev.id) {
              <div class="ev__history">
                @if (history(); as h) {
                  <div class="ev__hist-head">Versões</div>
                  @for (v of h.versions; track v.id) {
                    <small>v{{ v.version_number }} @if (v.is_current) { <b>(corrente)</b> } · {{ formatSize(v.size_bytes) }} · {{ shortHash(v.content_hash) }} · {{ formatDate(v.uploaded_at) }}</small>
                  }
                  <div class="ev__hist-head">Eventos de custódia</div>
                  @for (e of h.events; track e.id) {
                    <small>{{ e.event_type }} · {{ e.outcome }} · {{ formatDate(e.occurred_at) }}</small>
                  }
                } @else {
                  <small>Carregando histórico…</small>
                }
              </div>
            }
          }
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .ev { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); box-shadow: var(--wtn-e1); display: grid; gap: 10px; padding: 14px; }
    .ev__head { align-items: center; display: flex; gap: 12px; justify-content: space-between; }
    .ev__head strong { color: var(--wtn-text); font-size: 14px; }
    .ev__eyebrow { color: var(--wtn-muted); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .ev__upload { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; border: 1px dashed var(--wtn-border); border-radius: var(--wtn-r-md); padding: 9px 10px; }
    .ev__upload select, .ev__upload input[type=text] { background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text); padding: 5px 8px; }
    .ev__btn-primary { background: var(--wtn-primary); border: none; border-radius: var(--wtn-r-md); color: #fff; cursor: pointer; padding: 6px 14px; }
    .ev__btn-primary:disabled { opacity: .5; cursor: not-allowed; }
    .ev__empty { color: var(--wtn-text-2); font-size: 12.5px; }
    .ev__list { display: grid; gap: 8px; }
    .ev__row { align-items: center; border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); display: flex; gap: 10px; justify-content: space-between; padding: 9px 10px; }
    .ev__meta { display: grid; gap: 2px; }
    .ev__meta strong { color: var(--wtn-text); font-size: 12.5px; }
    .ev__meta span, .ev__meta small { color: var(--wtn-text-2); font-size: 11.5px; }
    .ev__actions { display: flex; gap: 6px; }
    .ev__actions button { align-items: center; background: var(--wtn-surface); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-md); color: var(--wtn-text-2); cursor: pointer; display: flex; height: 30px; justify-content: center; width: 30px; }
    .ev__actions button:hover:not(:disabled) { border-color: var(--wtn-border-strong); color: var(--wtn-primary); }
    .ev__actions button:disabled { opacity: .5; cursor: not-allowed; }
    .ev__history { border: 1px dashed var(--wtn-border); border-radius: var(--wtn-r-md); display: grid; gap: 3px; margin: -2px 0 6px; padding: 8px 10px; }
    .ev__hist-head { color: var(--wtn-muted); font-size: 10px; font-weight: 700; letter-spacing: .06em; margin-top: 4px; text-transform: uppercase; }
    .ev__history small { color: var(--wtn-text-2); font-size: 11px; }
  `,
})
export class EvidencePanel implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  readonly targetType = input.required<SgsiArtifactType>();
  readonly targetId = input.required<string>();
  readonly title = input('Evidências do artefato');
  readonly canManage = input(false);

  protected readonly loading = signal(false);
  protected readonly uploading = signal(false);
  protected readonly items = signal<EvidenceSummary[]>([]);
  protected readonly selectedFile = signal<File | null>(null);
  protected readonly historyOf = signal<string | null>(null);
  protected readonly history = signal<EvidenceHistory | null>(null);
  protected classification: Classification = 'uso_interno';
  protected uploadTitle = '';

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.listEvidence({ target_type: this.targetType(), target_id: this.targetId() }).subscribe({
      next: (rows) => {
        this.items.set(rows);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar evidências', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected onFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile.set(input.files?.[0] ?? null);
  }

  protected upload(event: Event): void {
    event.preventDefault();
    const file = this.selectedFile();
    if (!file) {
      return;
    }
    const form = new FormData();
    form.append('file', file);
    form.append('classification', this.classification);
    form.append('target_type', this.targetType());
    form.append('target_id', this.targetId());
    if (this.uploadTitle.trim()) {
      form.append('title', this.uploadTitle.trim());
    }
    this.uploading.set(true);
    this.api.uploadEvidence(form).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Evidência anexada' });
        this.selectedFile.set(null);
        this.uploadTitle = '';
        this.uploading.set(false);
        this.load();
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Falha ao anexar', detail: this.errorDetail(e) });
        this.uploading.set(false);
      },
    });
  }

  protected download(ev: EvidenceSummary): void {
    this.api.downloadEvidence(ev.id).subscribe({
      next: (blob) => this.downloadBlob(blob, ev.file_name),
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro ao baixar', detail: this.errorDetail(e) }),
    });
  }

  /** Substitui a evidência por uma nova versão (mantém a classificação corrente). */
  protected replaceFile(ev: EvidenceSummary, file: File): void {
    const form = new FormData();
    form.append('file', file);
    form.append('classification', ev.classification);
    this.api.replaceEvidence(ev.id, form).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Nova versão registrada' });
        if (this.historyOf() === ev.id) {
          this.loadHistory(ev);
        }
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Falha ao substituir', detail: this.errorDetail(e) }),
    });
  }

  protected triggerReplace(ev: EvidenceSummary): void {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = () => {
      const file = input.files?.[0];
      if (file) {
        this.replaceFile(ev, file);
      }
    };
    input.click();
  }

  protected toggleHistory(ev: EvidenceSummary): void {
    if (this.historyOf() === ev.id) {
      this.historyOf.set(null);
      this.history.set(null);
      return;
    }
    this.loadHistory(ev);
  }

  private loadHistory(ev: EvidenceSummary): void {
    this.historyOf.set(ev.id);
    this.history.set(null);
    this.api.evidenceHistory(ev.id).subscribe({
      next: (h) => this.history.set(h),
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar histórico', detail: this.errorDetail(e) });
        this.historyOf.set(null);
      },
    });
  }

  protected inactivate(ev: EvidenceSummary): void {
    this.api.inactivateEvidence(ev.id).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Evidência inativada' });
        this.load();
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro ao inativar', detail: this.errorDetail(e) }),
    });
  }

  protected classificationLabel(value: Classification): string {
    const labels: Record<Classification, string> = {
      publico: 'Público',
      uso_interno: 'Uso interno',
      confidencial: 'Confidencial',
      restrito: 'Restrito',
    };
    return labels[value];
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
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
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
