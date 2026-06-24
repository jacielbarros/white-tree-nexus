import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';
import { forkJoin } from 'rxjs';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import {
  Classification,
  DocumentPreview as Preview,
  PreviewLayout,
  PrintableDocumentType,
  SignaturePlacement,
  SignaturePlacementBase,
  SignedDocument,
} from '@app/core/models';
import { hasPermission } from '@app/core/permissions';
import { PdfSignatureViewer } from '@app/shared/pdf-signature-viewer/pdf-signature-viewer';

const SIGN_PERMISSION: Record<PrintableDocumentType, string> = {
  context_report: 'approve_context_document',
  gap_report: 'approve_gap_baseline',
  soa_report: 'approve_soa',
  gap_baseline: 'approve_gap_baseline',
  form_response: 'sign_form',
};

const CLASSIFICATION_OPTIONS: { label: string; value: Classification }[] = [
  { label: 'Uso interno', value: 'uso_interno' },
  { label: 'Publico', value: 'publico' },
  { label: 'Confidencial', value: 'confidencial' },
  { label: 'Restrito', value: 'restrito' },
];

@Component({
  selector: 'app-document-preview',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule, PdfSignatureViewer, ReactiveFormsModule, SelectModule],
  template: `
    <section class="doc-preview">
      <div class="doc-preview__head">
        <div>
          <div class="doc-preview__eyebrow">Documento controlado</div>
          <strong>{{ title() }}</strong>
        </div>
        <p-select
          [options]="classificationOptions"
          [formControl]="classification"
          optionLabel="label"
          optionValue="value"
          styleClass="doc-preview__select"
        />
      </div>

      @if (preview(); as p) {
        <div class="doc-preview__meta">
          <span>{{ statusLabel(p.status) }}</span>
          <span>Classificacao {{ p.classification }}</span>
          <span>Template {{ shortId(p.template_version_id) }}</span>
          <span>Expira {{ formatDate(p.expires_at) }}</span>
        </div>
        @if (p.warnings.length) {
          <div class="doc-preview__warning">
            @for (warning of p.warnings; track warning) {
              <span>{{ warning }}</span>
            }
          </div>
        }
        <div class="doc-preview__hash">Snapshot {{ shortHash(p.snapshot_hash) }}</div>
      } @else {
        <div class="doc-preview__empty">Nenhum preview gerado nesta sessao.</div>
      }

      @if (signed(); as doc) {
        <div class="doc-preview__signed">
          <strong>{{ doc.identifier }}</strong>
          <span>v{{ doc.version_number }} · {{ shortHash(doc.pdf_hash) }}</span>
        </div>
      }

      <div class="doc-preview__actions">
        <p-button
          label="Pre-visualizar"
          icon="pi pi-eye"
          (onClick)="generatePreview()"
          [loading]="loading()"
        />
        <p-button
          label="Baixar preliminar"
          icon="pi pi-download"
          severity="secondary"
          [disabled]="!preview()"
          (onClick)="downloadPreview()"
          [loading]="downloadingPreview()"
        />
        @if (canSign()) {
          <p-button
            label="Assinar"
            icon="pi pi-check-circle"
            severity="success"
            [disabled]="!preview() || preview()?.status !== 'active'"
            (onClick)="signPreview()"
            [loading]="signing()"
          />
        }
        <p-button
          label="Baixar assinado"
          icon="pi pi-file-pdf"
          severity="secondary"
          [disabled]="!signed()"
          (onClick)="downloadSigned()"
          [loading]="downloadingSigned()"
        />
      </div>

      @if (loadingInline()) {
        <div class="doc-preview__empty">Carregando preview inline...</div>
      }

      @if (previewPdf() && previewLayout()) {
        <app-pdf-signature-viewer
          [pdf]="previewPdf()"
          [layout]="previewLayout()"
          (placementConfirmed)="confirmPlacement($event)"
        />
      }

      @if (confirmedPlacement(); as placement) {
        <div class="doc-preview__placement">
          <strong>Posicao confirmada</strong>
          <span>rev. {{ placement.placement_revision }} - {{ shortHash(placement.placement_hash) }}</span>
        </div>
      } @else if (previewLayout()) {
        <div class="doc-preview__empty">Nenhuma posicao confirmada. Ao assinar, o sistema usara a posicao padrao validada.</div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }

    .doc-preview {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      display: grid;
      gap: 12px;
      padding: 14px;
    }

    .doc-preview__head {
      align-items: center;
      display: flex;
      gap: 12px;
      justify-content: space-between;
    }

    .doc-preview__head strong {
      color: var(--wtn-text);
      font-size: 14px;
      line-height: 1.2;
    }

    .doc-preview__eyebrow {
      color: var(--wtn-muted);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .doc-preview__select {
      min-width: 150px;
    }

    .doc-preview__meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .doc-preview__meta span,
    .doc-preview__hash,
    .doc-preview__signed span {
      color: var(--wtn-text-2);
      font-size: 12px;
    }

    .doc-preview__meta span {
      background: var(--wtn-surface-2);
      border-radius: var(--wtn-r-pill);
      padding: 3px 8px;
    }

    .doc-preview__empty {
      color: var(--wtn-text-2);
      font-size: 12.5px;
    }

    .doc-preview__warning {
      background: var(--wtn-warning-soft);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-warning);
      display: grid;
      font-size: 12px;
      gap: 2px;
      padding: 8px 10px;
    }

    .doc-preview__signed {
      background: var(--wtn-primary-soft);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-primary);
      display: grid;
      gap: 2px;
      padding: 8px 10px;
    }

    .doc-preview__placement {
      border-left: 3px solid var(--wtn-primary);
      color: var(--wtn-primary);
      display: grid;
      gap: 2px;
      padding: 4px 0 4px 10px;
    }

    .doc-preview__placement strong {
      font-size: 12px;
    }

    .doc-preview__placement span {
      color: var(--wtn-text-2);
      font-size: 11.5px;
    }

    .doc-preview__actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
  `,
})
export class DocumentPreview {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthStore);
  private readonly messages = inject(MessageService);

  readonly documentType = input.required<PrintableDocumentType>();
  readonly sourceArtifactId = input<string | null>(null);
  readonly title = input('Relatorio');

  protected readonly classification = new FormControl<Classification>('uso_interno', { nonNullable: true });
  protected readonly preview = signal<Preview | null>(null);
  protected readonly previewPdf = signal<Blob | null>(null);
  protected readonly previewLayout = signal<PreviewLayout | null>(null);
  protected readonly confirmedPlacement = signal<SignaturePlacement | null>(null);
  protected readonly signed = signal<SignedDocument | null>(null);
  protected readonly loading = signal(false);
  protected readonly loadingInline = signal(false);
  protected readonly confirmingPlacement = signal(false);
  protected readonly signing = signal(false);
  protected readonly downloadingPreview = signal(false);
  protected readonly downloadingSigned = signal(false);
  protected readonly classificationOptions = CLASSIFICATION_OPTIONS;

  protected readonly canSign = computed(() =>
    hasPermission(this.auth.currentRole(), SIGN_PERMISSION[this.documentType()]),
  );

  protected generatePreview(): void {
    this.loading.set(true);
    this.api.createDocumentPreview({
      document_type: this.documentType(),
      source_artifact_id: this.sourceArtifactId(),
      classification: this.classification.value,
    }).subscribe({
      next: (preview) => {
        this.preview.set(preview);
        this.previewPdf.set(null);
        this.previewLayout.set(null);
        this.confirmedPlacement.set(null);
        this.signed.set(null);
        this.loading.set(false);
        this.loadInlinePreview(preview);
        this.messages.add({ severity: 'success', summary: 'Preview gerado', life: 2500 });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao gerar preview', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected downloadPreview(): void {
    const preview = this.preview();
    if (!preview) return;
    this.downloadingPreview.set(true);
    this.api.downloadPreviewPdf(preview.id).subscribe({
      next: (blob) => {
        this.downloadBlob(blob, `${this.documentType()}-preview.pdf`);
        this.downloadingPreview.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao baixar preview', detail: this.errorDetail(e) });
        this.downloadingPreview.set(false);
      },
    });
  }

  protected signPreview(): void {
    const preview = this.preview();
    if (!preview) return;
    this.signing.set(true);
    this.api.signDocumentPreview(preview.id, preview.snapshot_hash, this.confirmedPlacement()?.id ?? null).subscribe({
      next: (doc) => {
        this.signed.set(doc);
        this.preview.update((p) => p ? { ...p, status: 'signed' } : p);
        this.signing.set(false);
        this.messages.add({ severity: 'success', summary: 'Documento assinado', detail: doc.identifier });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao assinar', detail: this.errorDetail(e) });
        this.signing.set(false);
      },
    });
  }

  protected confirmPlacement(placement: SignaturePlacementBase): void {
    const preview = this.preview();
    if (!preview) return;
    this.confirmingPlacement.set(true);
    this.api.confirmSignaturePlacement(preview.id, placement, preview.snapshot_hash).subscribe({
      next: (saved) => {
        this.confirmedPlacement.set(saved);
        this.previewLayout.update((layout) => layout ? { ...layout, latest_placement: saved } : layout);
        this.confirmingPlacement.set(false);
        this.messages.add({ severity: 'success', summary: 'Posicao confirmada', life: 2500 });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Posicao invalida', detail: this.errorDetail(e) });
        this.confirmingPlacement.set(false);
      },
    });
  }

  protected downloadSigned(): void {
    const doc = this.signed();
    if (!doc) return;
    this.downloadingSigned.set(true);
    this.api.downloadSignedPdf(doc.id).subscribe({
      next: (blob) => {
        this.downloadBlob(blob, `${doc.identifier}.pdf`);
        this.downloadingSigned.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao baixar assinado', detail: this.errorDetail(e) });
        this.downloadingSigned.set(false);
      },
    });
  }

  protected statusLabel(statusValue: string): string {
    const labels: Record<string, string> = {
      active: 'Preview ativo',
      expired: 'Preview expirado',
      stale: 'Preview desatualizado',
      signed: 'Assinado',
    };
    return labels[statusValue] ?? statusValue;
  }

  protected shortId(value: string): string {
    return value.slice(0, 8);
  }

  protected shortHash(value: string): string {
    return value.slice(0, 12);
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  }

  private loadInlinePreview(preview: Preview): void {
    this.loadingInline.set(true);
    forkJoin({
      pdf: this.api.openPreviewInlinePdf(preview.id),
      layout: this.api.getPreviewLayout(preview.id),
    }).subscribe({
      next: ({ pdf, layout }) => {
        this.previewPdf.set(pdf);
        this.previewLayout.set(layout);
        this.confirmedPlacement.set(layout.latest_placement);
        this.loadingInline.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao abrir preview', detail: this.errorDetail(e) });
        this.loadingInline.set(false);
      },
    });
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
    return 'Operacao nao concluida.';
  }
}
