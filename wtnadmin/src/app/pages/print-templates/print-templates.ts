import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { Classification, PrintableDocumentType, PrintTemplate, PrintTemplateVariable } from '@app/core/models';

type SignaturePage = 'first' | 'last';
type SignatureAnchor = 'bottom_right' | 'bottom_left' | 'top_right' | 'top_left';

interface SectionOption {
  key: string;
  title: string;
  description: string;
  requiredByDefault: boolean;
}

interface SignatureAppearance {
  default_page: SignaturePage;
  default_anchor: SignatureAnchor;
  default_margin_points: number;
  default_width_points: number;
  default_height_points: number;
}

const DOCUMENT_TYPES: { label: string; value: PrintableDocumentType }[] = [
  { label: 'Contexto', value: 'context_report' },
  { label: 'Gap Analysis', value: 'gap_report' },
  { label: 'SoA', value: 'soa_report' },
  { label: 'Baseline do Gap', value: 'gap_baseline' },
  { label: 'Resposta de formulario', value: 'form_response' },
];

const CLASSIFICATIONS: { label: string; value: Classification }[] = [
  { label: 'Uso interno', value: 'uso_interno' },
  { label: 'Publico', value: 'publico' },
  { label: 'Confidencial', value: 'confidencial' },
  { label: 'Restrito', value: 'restrito' },
];

const SIGNATURE_PAGES: { label: string; value: SignaturePage }[] = [
  { label: 'Ultima pagina', value: 'last' },
  { label: 'Primeira pagina', value: 'first' },
];

const SIGNATURE_ANCHORS: { label: string; value: SignatureAnchor }[] = [
  { label: 'Inferior direito', value: 'bottom_right' },
  { label: 'Inferior esquerdo', value: 'bottom_left' },
  { label: 'Superior direito', value: 'top_right' },
  { label: 'Superior esquerdo', value: 'top_left' },
];

const VALUE_TYPES = [
  { label: 'Texto', value: 'string' },
  { label: 'Numero', value: 'number' },
  { label: 'Data', value: 'date' },
  { label: 'Data/hora', value: 'datetime' },
  { label: 'Booleano', value: 'boolean' },
];

const DEFAULT_TITLES: Record<PrintableDocumentType, string> = {
  context_report: 'Relatorio de Contexto da Organizacao',
  gap_report: 'Relatorio de Gap Analysis',
  soa_report: 'Declaracao de Aplicabilidade (SoA)',
  gap_baseline: 'Baseline do Gap Analysis',
  form_response: 'Resposta de Formulario',
};

const SECTION_OPTIONS: Record<PrintableDocumentType, SectionOption[]> = {
  context_report: [
    {
      key: 'diagnostic',
      title: 'Diagnostico',
      description: 'Respostas do diagnostico de contexto.',
      requiredByDefault: true,
    },
    {
      key: 'analysis',
      title: 'Analise de contexto',
      description: 'Fatores internos, externos e registros estrategicos.',
      requiredByDefault: true,
    },
    {
      key: 'stakeholders',
      title: 'Partes interessadas',
      description: 'Necessidades e expectativas mapeadas.',
      requiredByDefault: true,
    },
    {
      key: 'scope',
      title: 'Escopo do SGSI',
      description: 'Declaracao de escopo consolidada.',
      requiredByDefault: true,
    },
  ],
  gap_report: [
    {
      key: 'summary',
      title: 'Resumo de aderencia',
      description: 'Indicadores gerais da avaliacao.',
      requiredByDefault: true,
    },
    {
      key: 'distribution',
      title: 'Distribuicao por status',
      description: 'Contagem de controles por classificacao.',
      requiredByDefault: false,
    },
    {
      key: 'items',
      title: 'Matriz de controles',
      description: 'Lista dos controles avaliados.',
      requiredByDefault: true,
    },
    {
      key: 'gaps',
      title: 'Lacunas priorizadas',
      description: 'Controles com maior criticidade.',
      requiredByDefault: false,
    },
  ],
  soa_report: [
    {
      key: 'summary',
      title: 'Resumo',
      description: 'Visao geral da declaracao.',
      requiredByDefault: true,
    },
    {
      key: 'items',
      title: 'Controles da SoA',
      description: 'Controles aplicaveis, justificativas e status.',
      requiredByDefault: true,
    },
    {
      key: 'divergences',
      title: 'Divergencias com Gap Analysis',
      description: 'Diferencas identificadas entre SoA e Gap.',
      requiredByDefault: false,
    },
  ],
  gap_baseline: [
    {
      key: 'summary',
      title: 'Resumo da baseline',
      description: 'Identificacao, data e responsavel pela baseline.',
      requiredByDefault: true,
    },
    {
      key: 'items',
      title: 'Controles consolidados',
      description: 'Estado congelado da matriz no momento da baseline.',
      requiredByDefault: true,
    },
    {
      key: 'changes',
      title: 'Alteracoes relevantes',
      description: 'Diferencas em relacao a versoes anteriores.',
      requiredByDefault: false,
    },
  ],
  form_response: [
    {
      key: 'summary',
      title: 'Resumo da resposta',
      description: 'Identificacao do formulario e respondente.',
      requiredByDefault: true,
    },
    {
      key: 'answers',
      title: 'Respostas',
      description: 'Campos preenchidos e respostas registradas.',
      requiredByDefault: true,
    },
    {
      key: 'signature',
      title: 'Assinatura',
      description: 'Metadados da assinatura eletronica.',
      requiredByDefault: false,
    },
  ],
};

const DEFAULT_REQUIRED_VARIABLES = ['organization_name', 'document_title', 'generated_at'];
const DEFAULT_OPTIONAL_VARIABLES = ['classification', 'document_status', 'source_reference'];
const DEFAULT_SIGNATURE: SignatureAppearance = {
  default_page: 'last',
  default_anchor: 'bottom_right',
  default_margin_points: 36,
  default_width_points: 180,
  default_height_points: 54,
};

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

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
                <span>{{ typeLabel(template.document_type) }} - {{ scopeLabel(template.scope) }} - {{ template.status }}</span>
              </button>
            } @empty {
              <div class="empty">Nenhum template disponivel.</div>
            }
          </div>
        }
      </div>

      <div class="template-panel template-panel--wide">
        <div class="panel-heading">
          <div>
            <h2>Nova versao</h2>
            <p>Configuracao guiada para gerar o layout versionado.</p>
          </div>
          @if (selected(); as template) {
            <span class="scope-pill" [class.scope-pill--system]="template.scope === 'system'">
              {{ scopeLabel(template.scope) }}
            </span>
          }
        </div>

        @if (selected(); as template) {
          <div class="selected">
            <strong>{{ template.name }}</strong>
            <span>{{ template.scope === 'system' ? 'Templates do sistema sao somente leitura.' : 'Pronto para criar uma nova versao tenant.' }}</span>
          </div>

          <form [formGroup]="versionBasicsForm" (ngSubmit)="createVersion(template)" class="form-stack">
            <div class="builder-grid">
              <label class="field-wide">
                Titulo do documento
                <input pInputText formControlName="title" />
              </label>

              <div class="builder-block field-wide">
                <div class="block-heading">
                  <h3>Secoes do documento</h3>
                  <span>{{ selectedSectionKeys().length }} selecionadas</span>
                </div>
                <div class="option-list">
                  @for (section of sectionOptions(template.document_type); track section.key) {
                    <label class="option-row">
                      <input
                        type="checkbox"
                        [checked]="isSectionSelected(section.key)"
                        (change)="toggleSection(section.key, $any($event.target).checked)"
                      />
                      <span>
                        <strong>{{ section.title }}</strong>
                        <em>{{ section.description }}</em>
                      </span>
                    </label>
                  }
                </div>
              </div>

              <div class="builder-block">
                <div class="block-heading">
                  <h3>Secoes obrigatorias</h3>
                  <span>{{ requiredSectionKeys().length }}</span>
                </div>
                <div class="option-list option-list--compact">
                  @for (section of selectedSections(template.document_type); track section.key) {
                    <label class="option-row option-row--compact">
                      <input
                        type="checkbox"
                        [checked]="isRequiredSection(section.key)"
                        (change)="toggleRequiredSection(section.key, $any($event.target).checked)"
                      />
                      <span>{{ section.title }}</span>
                    </label>
                  } @empty {
                    <div class="empty">Selecione ao menos uma secao.</div>
                  }
                </div>
              </div>

              <div class="builder-block">
                <div class="block-heading">
                  <h3>Variaveis</h3>
                  <span>{{ variablesLoading() ? 'Carregando...' : requiredVariableKeys().length + ' obrigatorias' }}</span>
                </div>
                <div class="variable-grid">
                  @for (variable of templateVariables(); track variable.id) {
                    <div class="variable-row">
                      <div class="variable-title">
                        <strong>{{ variable.label }}</strong>
                        <span class="scope-pill" [class.scope-pill--system]="variable.scope === 'system'">
                          {{ variableScopeLabel(variable) }}
                        </span>
                      </div>
                      <span>{{ variable.description || variable.variable_key }}</span>
                      <em>{{ variable.variable_key }} - {{ valueTypeLabel(variable.value_type) }}</em>
                      <div class="variable-actions">
                        <label>
                          <input
                            type="checkbox"
                            [checked]="isRequiredVariable(variable.variable_key)"
                            (change)="toggleVariable(variable.variable_key, 'required', $any($event.target).checked)"
                          />
                          Obrigatoria
                        </label>
                        <label>
                          <input
                            type="checkbox"
                            [checked]="isOptionalVariable(variable.variable_key)"
                            (change)="toggleVariable(variable.variable_key, 'optional', $any($event.target).checked)"
                          />
                          Opcional
                        </label>
                        @if (variable.scope === 'tenant') {
                          <button
                            type="button"
                            class="text-action"
                            (click)="deactivateVariable(variable, template)"
                          >
                            Inativar
                          </button>
                        }
                      </div>
                    </div>
                  } @empty {
                    <div class="empty">Nenhuma variavel disponivel para este tipo documental.</div>
                  }
                </div>

                @if (template.scope === 'tenant') {
                  <div class="variable-create" [formGroup]="variableForm">
                    <label>
                      Chave
                      <input pInputText formControlName="variable_key" placeholder="ex: audit_cycle" />
                    </label>
                    <label>
                      Rotulo
                      <input pInputText formControlName="label" placeholder="Ciclo de auditoria" />
                    </label>
                    <label>
                      Tipo
                      <p-select
                        [options]="valueTypes"
                        formControlName="value_type"
                        optionLabel="label"
                        optionValue="value"
                        styleClass="w-full"
                      />
                    </label>
                    <label class="field-wide">
                      Descricao
                      <input pInputText formControlName="description" />
                    </label>
                    <label class="inline-check">
                      <input
                        type="checkbox"
                        formControlName="required_by_default"
                        (change)="variableForm.controls.optional_by_default.setValue(!$any($event.target).checked)"
                      />
                      Obrigatoria por padrao
                    </label>
                    <label class="inline-check">
                      <input
                        type="checkbox"
                        formControlName="optional_by_default"
                        (change)="variableForm.controls.required_by_default.setValue(!$any($event.target).checked && variableForm.controls.required_by_default.value)"
                      />
                      Opcional por padrao
                    </label>
                    <p-button
                      type="button"
                      label="Adicionar variavel"
                      icon="pi pi-plus"
                      [loading]="creatingVariable()"
                      (onClick)="createVariable(template)"
                    />
                  </div>
                }
              </div>

              <div class="builder-block field-wide">
                <div class="block-heading">
                  <h3>Selo de assinatura</h3>
                  <span>{{ signatureAnchorLabel() }}</span>
                </div>
                <div class="signature-grid">
                  <label>
                    Pagina padrao
                    <p-select
                      [options]="signaturePages"
                      formControlName="signature_page"
                      optionLabel="label"
                      optionValue="value"
                      styleClass="w-full"
                    />
                  </label>
                  <label>
                    Posicao padrao
                    <p-select
                      [options]="signatureAnchors"
                      formControlName="signature_anchor"
                      optionLabel="label"
                      optionValue="value"
                      styleClass="w-full"
                    />
                  </label>
                  <label>
                    Margem (pt)
                    <input pInputText type="number" min="0" formControlName="signature_margin_points" />
                  </label>
                  <label>
                    Largura (pt)
                    <input pInputText type="number" min="96" max="260" formControlName="signature_width_points" />
                  </label>
                  <label>
                    Altura (pt)
                    <input pInputText type="number" min="32" max="96" formControlName="signature_height_points" />
                  </label>
                </div>
              </div>
            </div>

            <div class="advanced-bar">
              <p-button
                type="button"
                [label]="advancedMode() ? 'Ocultar JSON' : 'Modo avancado JSON'"
                icon="pi pi-code"
                severity="secondary"
                outlined
                (onClick)="toggleAdvanced()"
              />
            </div>

            @if (advancedMode()) {
              <div class="advanced-fields" [formGroup]="versionForm">
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
              </div>
            }

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
      grid-template-columns: minmax(280px, 340px) minmax(320px, 1fr);
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

    .template-panel h2,
    .builder-block h3 {
      color: var(--wtn-text);
      font-size: 15px;
      margin: 0;
    }

    .builder-block h3 {
      font-size: 13px;
    }

    .panel-heading,
    .block-heading,
    .advanced-bar {
      align-items: center;
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }

    .panel-heading p,
    .block-heading span,
    .template-row span,
    .selected span,
    .empty,
    .variable-row span {
      color: var(--wtn-text-2);
      font-size: 12px;
      margin: 0;
    }

    .form-stack,
    .template-list,
    .option-list,
    .advanced-fields {
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
    .selected strong,
    .variable-row strong {
      color: var(--wtn-text);
      font-size: 13px;
    }

    .selected {
      background: var(--wtn-primary-soft);
      border-radius: var(--wtn-r-md);
      display: grid;
      gap: 2px;
      padding: 9px 10px;
    }

    .scope-pill {
      background: color-mix(in srgb, var(--wtn-primary) 18%, transparent);
      border-radius: 999px;
      color: var(--wtn-primary);
      font-size: 11px;
      font-weight: 800;
      padding: 5px 9px;
      text-transform: uppercase;
    }

    .scope-pill--system {
      background: color-mix(in srgb, var(--wtn-text-2) 18%, transparent);
      color: var(--wtn-text-2);
    }

    .builder-grid {
      display: grid;
      gap: 14px;
      grid-template-columns: minmax(280px, 0.9fr) minmax(360px, 1.1fr);
    }

    .field-wide {
      grid-column: 1 / -1;
    }

    .builder-block {
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-md);
      display: grid;
      gap: 12px;
      padding: 12px;
    }

    .option-row {
      align-items: start;
      border-bottom: 1px solid color-mix(in srgb, var(--wtn-border) 70%, transparent);
      display: grid;
      gap: 10px;
      grid-template-columns: 18px 1fr;
      padding: 8px 0;
    }

    .option-row:last-child {
      border-bottom: 0;
    }

    .option-row input,
    .variable-actions input {
      accent-color: var(--wtn-primary);
      width: auto;
    }

    .option-row span {
      display: grid;
      gap: 3px;
    }

    .option-row em {
      color: var(--wtn-text-2);
      font-style: normal;
      font-weight: 500;
    }

    .option-row--compact {
      align-items: center;
      padding: 6px 0;
    }

    .variable-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
    }

    .variable-row {
      border-bottom: 1px solid color-mix(in srgb, var(--wtn-border) 70%, transparent);
      display: grid;
      gap: 6px;
      padding: 8px 0;
    }

    .variable-title {
      align-items: center;
      display: flex;
      gap: 8px;
      justify-content: space-between;
    }

    .variable-row em {
      color: var(--wtn-text-2);
      font-size: 11px;
      font-style: normal;
      font-weight: 700;
    }

    .variable-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }

    .variable-actions label {
      align-items: center;
      display: flex;
      font-weight: 700;
      gap: 5px;
    }

    .variable-create {
      border-top: 1px solid var(--wtn-border);
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(3, minmax(120px, 1fr));
      padding-top: 12px;
    }

    .inline-check {
      align-items: center;
      display: flex;
      gap: 7px;
    }

    .inline-check input {
      width: auto;
    }

    .text-action {
      background: transparent;
      border: 0;
      color: var(--wtn-danger, #ef7f73);
      cursor: pointer;
      font-size: 12px;
      font-weight: 800;
      padding: 0;
    }

    .signature-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(5, minmax(120px, 1fr));
    }

    @media (max-width: 1120px) {
      .builder-grid,
      .signature-grid,
      .variable-grid,
      .variable-create {
        grid-template-columns: 1fr;
      }
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
  protected readonly signaturePages = SIGNATURE_PAGES;
  protected readonly signatureAnchors = SIGNATURE_ANCHORS;
  protected readonly valueTypes = VALUE_TYPES;
  protected readonly loading = signal(false);
  protected readonly variablesLoading = signal(false);
  protected readonly creating = signal(false);
  protected readonly creatingVariable = signal(false);
  protected readonly creatingVersion = signal(false);
  protected readonly advancedMode = signal(false);
  protected readonly templates = signal<PrintTemplate[]>([]);
  protected readonly templateVariables = signal<PrintTemplateVariable[]>([]);
  protected readonly selected = signal<PrintTemplate | null>(null);
  protected readonly selectedSectionKeys = signal<string[]>([]);
  protected readonly requiredSectionKeys = signal<string[]>([]);
  protected readonly requiredVariableKeys = signal<string[]>([...DEFAULT_REQUIRED_VARIABLES]);
  protected readonly optionalVariableKeys = signal<string[]>([...DEFAULT_OPTIONAL_VARIABLES]);

  protected readonly templateForm = this.fb.group({
    document_type: this.fb.control<PrintableDocumentType>('gap_report'),
    name: '',
    description: '',
    default_classification: this.fb.control<Classification>('uso_interno'),
  });

  protected readonly versionBasicsForm = this.fb.group({
    title: DEFAULT_TITLES.gap_report,
    signature_page: this.fb.control<SignaturePage>(DEFAULT_SIGNATURE.default_page),
    signature_anchor: this.fb.control<SignatureAnchor>(DEFAULT_SIGNATURE.default_anchor),
    signature_margin_points: DEFAULT_SIGNATURE.default_margin_points,
    signature_width_points: DEFAULT_SIGNATURE.default_width_points,
    signature_height_points: DEFAULT_SIGNATURE.default_height_points,
  });

  protected readonly versionForm = this.fb.group({
    layout_schema: '',
    allowed_variables: '',
    required_sections: '',
  });

  protected readonly variableForm = this.fb.group({
    variable_key: '',
    label: '',
    description: '',
    value_type: 'string',
    required_by_default: false,
    optional_by_default: true,
  });

  ngOnInit(): void {
    this.applyDocumentDefaults('gap_report');
    this.loadVariables('gap_report', true);
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

  protected loadVariables(documentType: PrintableDocumentType, resetDefaults = false): void {
    this.variablesLoading.set(true);
    this.api.listPrintTemplateVariables(documentType).subscribe({
      next: (rows) => {
        this.templateVariables.set(rows);
        if (resetDefaults) this.applyVariableDefaults(rows, documentType);
        this.variablesLoading.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao carregar variaveis', detail: this.errorDetail(e) });
        this.templateVariables.set(this.fallbackVariables(documentType));
        if (resetDefaults) this.applyVariableDefaults(this.templateVariables(), documentType);
        this.variablesLoading.set(false);
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
        this.applyDocumentDefaults(template.document_type);
        this.loadVariables(template.document_type, true);
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
    this.applyDocumentDefaults(template.document_type);
    this.loadVariables(template.document_type, true);
  }

  protected createVariable(template: PrintTemplate): void {
    const key = this.variableForm.controls.variable_key.value.trim();
    const label = this.variableForm.controls.label.value.trim();
    if (!key || !label) {
      this.messages.add({ severity: 'warn', summary: 'Chave e rotulo obrigatorios' });
      return;
    }
    this.creatingVariable.set(true);
    this.api.createPrintTemplateVariable({
      document_type: template.document_type,
      variable_key: key,
      label,
      description: this.variableForm.controls.description.value.trim() || null,
      value_type: this.variableForm.controls.value_type.value,
      required_by_default: this.variableForm.controls.required_by_default.value,
      optional_by_default: this.variableForm.controls.optional_by_default.value,
      sort_order: 500,
    }).subscribe({
      next: (variable) => {
        this.templateVariables.update((rows) => [...rows, variable].sort(this.variableSort));
        if (variable.required_by_default) this.toggleVariable(variable.variable_key, 'required', true);
        if (variable.optional_by_default) this.toggleVariable(variable.variable_key, 'optional', true);
        this.variableForm.reset({
          variable_key: '',
          label: '',
          description: '',
          value_type: 'string',
          required_by_default: false,
          optional_by_default: true,
        });
        this.syncAdvancedJson(template.document_type);
        this.creatingVariable.set(false);
        this.messages.add({ severity: 'success', summary: 'Variavel criada', detail: variable.label });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao criar variavel', detail: this.errorDetail(e) });
        this.creatingVariable.set(false);
      },
    });
  }

  protected deactivateVariable(variable: PrintTemplateVariable, template: PrintTemplate): void {
    if (variable.scope !== 'tenant') return;
    this.api.deactivatePrintTemplateVariable(variable.id).subscribe({
      next: (updated) => {
        this.templateVariables.update((rows) => rows.filter((row) => row.id !== updated.id));
        this.requiredVariableKeys.update((keys) => keys.filter((item) => item !== updated.variable_key));
        this.optionalVariableKeys.update((keys) => keys.filter((item) => item !== updated.variable_key));
        this.syncAdvancedJson(template.document_type);
        this.messages.add({ severity: 'success', summary: 'Variavel inativada', detail: updated.label });
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro ao inativar variavel', detail: this.errorDetail(e) });
      },
    });
  }

  protected createVersion(template: PrintTemplate): void {
    if (template.scope === 'system') return;
    if (!this.advancedMode()) this.syncAdvancedJson();

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
    if (sections.length === 0) {
      this.messages.add({ severity: 'warn', summary: 'Selecione secoes obrigatorias' });
      return;
    }
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

  protected toggleAdvanced(): void {
    if (!this.advancedMode()) this.syncAdvancedJson();
    this.advancedMode.update((value) => !value);
  }

  protected sectionOptions(documentType: PrintableDocumentType): SectionOption[] {
    return SECTION_OPTIONS[documentType];
  }

  protected selectedSections(documentType: PrintableDocumentType): SectionOption[] {
    const selected = new Set(this.selectedSectionKeys());
    return this.sectionOptions(documentType).filter((section) => selected.has(section.key));
  }

  protected isSectionSelected(key: string): boolean {
    return this.selectedSectionKeys().includes(key);
  }

  protected toggleSection(key: string, checked: boolean): void {
    if (checked) {
      this.selectedSectionKeys.update((keys) => unique([...keys, key]));
      return;
    }
    this.selectedSectionKeys.update((keys) => keys.filter((item) => item !== key));
    this.requiredSectionKeys.update((keys) => keys.filter((item) => item !== key));
  }

  protected isRequiredSection(key: string): boolean {
    return this.requiredSectionKeys().includes(key);
  }

  protected toggleRequiredSection(key: string, checked: boolean): void {
    if (!this.isSectionSelected(key)) return;
    this.requiredSectionKeys.update((keys) => checked ? unique([...keys, key]) : keys.filter((item) => item !== key));
  }

  protected isRequiredVariable(key: string): boolean {
    return this.requiredVariableKeys().includes(key);
  }

  protected isOptionalVariable(key: string): boolean {
    return this.optionalVariableKeys().includes(key);
  }

  protected toggleVariable(key: string, type: 'required' | 'optional', checked: boolean): void {
    if (type === 'required') {
      this.requiredVariableKeys.update((keys) => checked ? unique([...keys, key]) : keys.filter((item) => item !== key));
      if (checked) this.optionalVariableKeys.update((keys) => keys.filter((item) => item !== key));
      return;
    }
    this.optionalVariableKeys.update((keys) => checked ? unique([...keys, key]) : keys.filter((item) => item !== key));
    if (checked) this.requiredVariableKeys.update((keys) => keys.filter((item) => item !== key));
  }

  protected variableScopeLabel(variable: PrintTemplateVariable): string {
    return variable.scope === 'system' ? 'Sistema' : 'Tenant';
  }

  protected valueTypeLabel(value: string): string {
    return VALUE_TYPES.find((item) => item.value === value)?.label ?? value;
  }

  protected typeLabel(value: string): string {
    return DOCUMENT_TYPES.find((item) => item.value === value)?.label ?? value;
  }

  protected scopeLabel(value: string): string {
    return value === 'system' ? 'Sistema' : 'Tenant';
  }

  protected signatureAnchorLabel(): string {
    const anchor = this.versionBasicsForm.controls.signature_anchor.value;
    return SIGNATURE_ANCHORS.find((item) => item.value === anchor)?.label ?? anchor;
  }

  private applyDocumentDefaults(documentType: PrintableDocumentType): void {
    const sections = SECTION_OPTIONS[documentType];
    const selected = sections.map((section) => section.key);
    const required = sections.filter((section) => section.requiredByDefault).map((section) => section.key);
    this.versionBasicsForm.patchValue({
      title: DEFAULT_TITLES[documentType],
      signature_page: DEFAULT_SIGNATURE.default_page,
      signature_anchor: DEFAULT_SIGNATURE.default_anchor,
      signature_margin_points: DEFAULT_SIGNATURE.default_margin_points,
      signature_width_points: DEFAULT_SIGNATURE.default_width_points,
      signature_height_points: DEFAULT_SIGNATURE.default_height_points,
    });
    this.selectedSectionKeys.set(selected);
    this.requiredSectionKeys.set(required);
    this.requiredVariableKeys.set([...DEFAULT_REQUIRED_VARIABLES]);
    this.optionalVariableKeys.set([...DEFAULT_OPTIONAL_VARIABLES]);
    this.syncAdvancedJson(documentType);
  }

  private applyVariableDefaults(rows: PrintTemplateVariable[], documentType: PrintableDocumentType): void {
    const active = rows.filter((row) => row.document_type === documentType && row.status === 'active');
    const required = active.filter((row) => row.required_by_default).map((row) => row.variable_key);
    const optional = active
      .filter((row) => row.optional_by_default && !required.includes(row.variable_key))
      .map((row) => row.variable_key);
    this.requiredVariableKeys.set(required.length ? required : [...DEFAULT_REQUIRED_VARIABLES]);
    this.optionalVariableKeys.set(optional.length ? optional : [...DEFAULT_OPTIONAL_VARIABLES]);
    this.syncAdvancedJson(documentType);
  }

  private fallbackVariables(documentType: PrintableDocumentType): PrintTemplateVariable[] {
    const now = new Date().toISOString();
    return [
      ...DEFAULT_REQUIRED_VARIABLES.map((key, index) => ({
        id: `fallback-required-${documentType}-${key}`,
        tenant_id: null,
        scope: 'system' as const,
        document_type: documentType,
        variable_key: key,
        label: key,
        description: null,
        value_type: 'string',
        required_by_default: true,
        optional_by_default: false,
        status: 'active' as const,
        sort_order: (index + 1) * 10,
        created_at: now,
        updated_at: null,
      })),
      ...DEFAULT_OPTIONAL_VARIABLES.map((key, index) => ({
        id: `fallback-optional-${documentType}-${key}`,
        tenant_id: null,
        scope: 'system' as const,
        document_type: documentType,
        variable_key: key,
        label: key,
        description: null,
        value_type: 'string',
        required_by_default: false,
        optional_by_default: true,
        status: 'active' as const,
        sort_order: 100 + (index + 1) * 10,
        created_at: now,
        updated_at: null,
      })),
    ];
  }

  private variableSort(a: PrintTemplateVariable, b: PrintTemplateVariable): number {
    return a.sort_order - b.sort_order || a.label.localeCompare(b.label);
  }

  private syncAdvancedJson(documentType = this.selected()?.document_type ?? this.templateForm.controls.document_type.value): void {
    const layout = this.buildLayoutSchema(documentType);
    const variables = {
      required: this.requiredVariableKeys(),
      optional: this.optionalVariableKeys(),
    };
    this.versionForm.setValue({
      layout_schema: JSON.stringify(layout, null, 2),
      allowed_variables: JSON.stringify(variables, null, 2),
      required_sections: this.requiredSectionKeys().join(','),
    });
  }

  private buildLayoutSchema(documentType: PrintableDocumentType): Record<string, unknown> {
    const selected = new Set(this.selectedSectionKeys());
    const sections = this.sectionOptions(documentType)
      .filter((section) => selected.has(section.key))
      .map((section) => ({ key: section.key, title: section.title }));
    return {
      title: this.versionBasicsForm.controls.title.value.trim() || DEFAULT_TITLES[documentType],
      sections,
      signature_appearance: {
        default_page: this.versionBasicsForm.controls.signature_page.value,
        default_anchor: this.versionBasicsForm.controls.signature_anchor.value,
        default_margin_points: this.numberValue(this.versionBasicsForm.controls.signature_margin_points.value, DEFAULT_SIGNATURE.default_margin_points),
        default_width_points: this.numberValue(this.versionBasicsForm.controls.signature_width_points.value, DEFAULT_SIGNATURE.default_width_points),
        default_height_points: this.numberValue(this.versionBasicsForm.controls.signature_height_points.value, DEFAULT_SIGNATURE.default_height_points),
        min_width_points: 96,
        min_height_points: 32,
        max_width_points: 260,
        max_height_points: 96,
        blocked_areas: [],
      },
    };
  }

  private numberValue(value: number | string, fallback: number): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
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
