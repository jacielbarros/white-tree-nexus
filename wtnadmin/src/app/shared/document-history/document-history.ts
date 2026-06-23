import { ChangeDetectionStrategy, Component, OnInit, inject, input, signal } from '@angular/core';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { PrintableDocumentType, SignedDocument } from '@app/core/models';

@Component({
  selector: 'app-document-history',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule],
  template: `
    <section class="doc-history">
      <div class="doc-history__head">
        <div>
          <div class="doc-history__eyebrow">Historico assinado</div>
          <strong>{{ title() }}</strong>
        </div>
        <p-button
          icon="pi pi-refresh"
          label="Atualizar"
          severity="secondary"
          (onClick)="load()"
          [loading]="loading()"
        />
      </div>

      @if (loading()) {
        <div class="doc-history__empty">Carregando documentos...</div>
      } @else if (!documents().length) {
        <div class="doc-history__empty">Nenhum documento assinado ainda.</div>
      } @else {
        <div class="doc-history__list">
          @for (doc of documents(); track doc.id) {
            <div class="doc-history__row">
              <div>
                <strong>{{ doc.identifier }}</strong>
                <span>
                  v{{ doc.version_number }} · {{ statusLabel(doc.status) }} · {{ formatDate(doc.signed_at) }}
                </span>
                <small>{{ shortHash(doc.pdf_hash) }}</small>
              </div>
              <div class="doc-history__actions">
                <button type="button" (click)="download(doc)" title="Baixar PDF">
                  <span class="pi pi-download"></span>
                </button>
                <button type="button" (click)="verify(doc)" title="Verificar integridade">
                  <span class="pi pi-shield"></span>
                </button>
              </div>
            </div>
          }
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }

    .doc-history {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      display: grid;
      gap: 10px;
      padding: 14px;
    }

    .doc-history__head {
      align-items: center;
      display: flex;
      gap: 12px;
      justify-content: space-between;
    }

    .doc-history__head strong {
      color: var(--wtn-text);
      font-size: 14px;
    }

    .doc-history__eyebrow {
      color: var(--wtn-muted);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .doc-history__empty {
      color: var(--wtn-text-2);
      font-size: 12.5px;
    }

    .doc-history__list {
      display: grid;
      gap: 8px;
    }

    .doc-history__row {
      align-items: center;
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-md);
      display: flex;
      gap: 10px;
      justify-content: space-between;
      padding: 9px 10px;
    }

    .doc-history__row div:first-child {
      display: grid;
      gap: 2px;
    }

    .doc-history__row strong {
      color: var(--wtn-text);
      font-size: 12.5px;
    }

    .doc-history__row span,
    .doc-history__row small {
      color: var(--wtn-text-2);
      font-size: 11.5px;
    }

    .doc-history__actions {
      display: flex;
      gap: 6px;
    }

    .doc-history__actions button {
      align-items: center;
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text-2);
      cursor: pointer;
      display: flex;
      height: 30px;
      justify-content: center;
      width: 30px;
    }

    .doc-history__actions button:hover {
      border-color: var(--wtn-border-strong);
      color: var(--wtn-primary);
    }
  `,
})
export class DocumentHistory implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  readonly documentType = input.required<PrintableDocumentType>();
  readonly sourceArtifactId = input<string | null>(null);
  readonly title = input('Versoes');

  protected readonly loading = signal(false);
  protected readonly documents = signal<SignedDocument[]>([]);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.listSignedDocuments(this.documentType(), this.sourceArtifactId()).subscribe({
      next: (rows) => {
        this.documents.set(rows);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar historico', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected download(doc: SignedDocument): void {
    this.api.downloadSignedPdf(doc.id).subscribe({
      next: (blob) => this.downloadBlob(blob, `${doc.identifier}.pdf`),
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro ao baixar PDF', detail: this.errorDetail(e) }),
    });
  }

  protected verify(doc: SignedDocument): void {
    this.api.verifySignedDocument(doc.id).subscribe({
      next: (result) => {
        this.messages.add({
          severity: result.valid ? 'success' : 'warn',
          summary: result.valid ? 'Integridade confirmada' : 'Integridade invalida',
          detail: result.identifier,
        });
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro ao verificar', detail: this.errorDetail(e) }),
    });
  }

  protected statusLabel(value: string): string {
    return value === 'obsolete' ? 'Obsoleto' : 'Assinado';
  }

  protected shortHash(value: string): string {
    return value.slice(0, 12);
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
    return 'Operacao nao concluida.';
  }
}
