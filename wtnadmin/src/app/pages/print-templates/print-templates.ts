import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { Classification, PrintableDocumentType, PrintTemplate } from '@app/core/models';

const DOCUMENT_TYPES: { label: string; value: PrintableDocumentType }[] = [
  { label: 'Contexto', value: 'context_report' },
  { label: 'Gap Analysis', value: 'gap_report' },
  { label: 'SoA', value: 'soa_report' },
];

const CLASSIFICATIONS: { label: string; value: Classification }[] = [
  { label: 'Uso interno', value: 'uso_interno' },
  { label: 'Publico', value: 'publico' },
  { label: 'Confidencial', value: 'confidencial' },
  { label: 'Restrito', value: 'restrito' },
];

const DEFAULT_LAYOUT = JSON.stringify({
  title: 'Documento SGSI',
  sections: [
    { key: 'summary', title: 'Resumo' },
    { key: 'items', title: 'Itens' },
  ],
}, null, 2);

const DEFAULT_VARIABLES = JSON.stringify({
  required: ['organization_name', 'document_title', 'generated_at'],
  optional: ['classification', 'document_status', 'source_reference'],
}, null, 2);

@Component({
  selector: 'app-print-templates-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule, InputTextModule, ReactiveFormsModule, SelectModule, TextareaModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Templates de impressao</h1>
        <p class="wtn-page-desc">Modelos versionados usados por previews e documentos assinados.</p>
      </div>
    </header>

    <section class="template-grid">
      <div class="template-panel">
        <h2>Novo template</h2>
        <form [formGroup]="templateForm" (ngSubmit)="createTemplate()" class="form-stack">
          <label>
            Tipo documental
            <p-select
              [options]="documentTypes"
              formControlName="document_type"
              optionLabel="label"
              optionValue="value"
              styleClass="w-full"
            />
          </label>
          <label>
            Nome
            <input pInputText formControlName="name" />
          </label>
          <label>
            Descricao
            <input pInputText formControlName="description" />
          </label>
          <label>
            Classificacao padrao
            <p-select
              [options]="classifications"
              formControlName="default_classification"
              optionLabel="label"
              optionValue="value"
              styleClass="w-full"
            />
          </label>
          <p-button type="submit" label="Criar template" icon="pi pi-plus" [loading]="creating()" />
        </form>
      </div>

      <div class="template-panel">
        <h2>Templates visiveis</h2>
        @if (loading()) {
          <div class="empty">Carregando...</div>
        } @else {
          <div class="template-list">
            @for (template of templates(); track template.id) {
              <button
                type="button"
                class="template-row"
                [class.template-row--selected]="selected()?.id === template.id"
                (click)="select(template)"
              >
                <strong>{{ template.name }}</strong>
                <span>{{ typeLabel(template.document_type) }} · {{ template.scope }} · {{ template.status }}</span>
              </button>
            } @empty {
              <div class="empty">Nenhum template disponivel.</div>
            }
          </div>
        }
      </div>

      <div class="template-panel template-panel--wide">
        <h2>Nova versao</h2>
        @if (selected(); as template) {
          <div class="selected">
            <strong>{{ template.name }}</strong>
            <span>{{ template.scope === 'system' ? 'Templates do sistema sao somente leitura.' : 'Template tenant editavel.' }}</span>
          </div>
          <form [formGroup]="versionForm" (ngSubmit)="createVersion(template)" class="form-stack">
            <label>
              Layout JSON
              <textarea pTextarea formControlName="layout_schema" rows="8"></textarea>
            </label>
            <label>
              Variaveis permitidas JSON
              <textarea pTextarea formControlName="allowed_variables" rows="5"></textarea>
            </label>
            <label>
              Secoes obrigatorias
              <input pInputText formControlName="required_sections" placeholder="summary,items" />
            </label>
            <p-button
              type="submit"
              label="Criar e ativar versao"
              icon="pi pi-check"
              [disabled]="template.scope === 'system'"
              [loading]="creatingVersion()"
            />
          </form>
        } @else {
          <div class="empty">Selecione um template tenant para criar uma versao.</div>
        }
      </div>
    </section>
  `,
  styles: `
    :host { display: block; }

    .template-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: 340px minmax(320px, 1fr);
    }

    .template-panel {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      display: grid;
      gap: 12px;
      padding: 16px;
    }

    .template-panel--wide {
      grid-column: 1 / -1;
    }

    .template-panel h2 {
      color: var(--wtn-text);
      font-size: 15px;
      margin: 0;
    }

    .form-stack {
      display: grid;
      gap: 11px;
    }

    label {
      color: var(--wtn-text-2);
      display: grid;
      font-size: 12px;
      font-weight: 600;
      gap: 5px;
    }

    input,
    textarea {
      width: 100%;
    }

    .template-list {
      display: grid;
      gap: 8px;
    }

    .template-row {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-md);
      color: inherit;
      cursor: pointer;
      display: grid;
      gap: 3px;
      padding: 10px;
      text-align: left;
    }

    .template-row--selected,
    .template-row:hover {
      border-color: var(--wtn-primary);
    }

    .template-row strong,
    .selected strong {
      color: var(--wtn-text);
      font-size: 13px;
    }

    .template-row span,
    .selected span,
    .empty {
      color: var(--wtn-text-2);
      font-size: 12px;
    }

    .selected {
      background: var(--wtn-primary-soft);
      border-radius: var(--wtn-r-md);
      display: grid;
      gap: 2px;
      padding: 9px 10px;
    }

    @media (max-width: 980px) {
      .template-grid {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class PrintTemplatesPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly messages = inject(MessageService);

  protected readonly documentTypes = DOCUMENT_TYPES;
  protected readonly classifications = CLASSIFICATIONS;
  protected readonly loading = signal(false);
  protected readonly creating = signal(false);
  protected readonly creatingVersion = signal(false);
  protected readonly templates = signal<PrintTemplate[]>([]);
  protected readonly selected = signal<PrintTemplate | null>(null);

  protected readonly templateForm = this.fb.group({
    document_type: this.fb.control<PrintableDocumentType>('gap_report'),
    name: '',
    description: '',
    default_classification: this.fb.control<Classification>('uso_interno'),
  });

  protected readonly versionForm = this.fb.group({
    layout_schema: DEFAULT_LAYOUT,
    allowed_variables: DEFAULT_VARIABLES,
    required_sections: 'summary,items',
  });

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.listPrintTemplates().subscribe({
      next: (rows) => {
        this.templates.set(rows);
        this.loading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar templates', detail: this.errorDetail(e) });
        this.loading.set(false);
      },
    });
  }

  protected createTemplate(): void {
    if (!this.templateForm.controls.name.value.trim()) {
      this.messages.add({ severity: 'warn', summary: 'Nome obrigatorio' });
      return;
    }
    this.creating.set(true);
    this.api.createPrintTemplate({
      document_type: this.templateForm.controls.document_type.value,
      name: this.templateForm.controls.name.value.trim(),
      description: this.templateForm.controls.description.value.trim() || null,
      default_classification: this.templateForm.controls.default_classification.value,
    }).subscribe({
      next: (template) => {
        this.templates.update((rows) => [template, ...rows]);
        this.selected.set(template);
        this.creating.set(false);
        this.messages.add({ severity: 'success', summary: 'Template criado', detail: template.name });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao criar template', detail: this.errorDetail(e) });
        this.creating.set(false);
      },
    });
  }

  protected select(template: PrintTemplate): void {
    this.selected.set(template);
  }

  protected createVersion(template: PrintTemplate): void {
    if (template.scope === 'system') return;
    let layout: Record<string, unknown>;
    let variables: Record<string, unknown>;
    try {
      layout = JSON.parse(this.versionForm.controls.layout_schema.value) as Record<string, unknown>;
      variables = JSON.parse(this.versionForm.controls.allowed_variables.value) as Record<string, unknown>;
    } catch {
      this.messages.add({ severity: 'warn', summary: 'JSON invalido' });
      return;
    }
    const sections = this.versionForm.controls.required_sections.value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    this.creatingVersion.set(true);
    this.api.createPrintTemplateVersion(template.id, {
      layout_schema: layout,
      allowed_variables: variables,
      required_sections: sections,
    }).subscribe({
      next: (version) => {
        this.api.activatePrintTemplateVersion(template.id, version.id).subscribe({
          next: (updated) => {
            this.templates.update((rows) => rows.map((row) => row.id === updated.id ? updated : row));
            this.selected.set(updated);
            this.creatingVersion.set(false);
            this.messages.add({ severity: 'success', summary: 'Versao ativada', detail: `v${version.version_number}` });
          },
          error: (e) => {
            this.messages.add({ severity: 'error', summary: 'Erro ao ativar', detail: this.errorDetail(e) });
            this.creatingVersion.set(false);
          },
        });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao criar versao', detail: this.errorDetail(e) });
        this.creatingVersion.set(false);
      },
    });
  }

  protected typeLabel(value: string): string {
    return DOCUMENT_TYPES.find((item) => item.value === value)?.label ?? value;
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
