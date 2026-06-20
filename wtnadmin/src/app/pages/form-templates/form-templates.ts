import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { FormField, FormKind, FormTemplate, TemplateStatus } from '@app/core/models';

const KIND_LABELS: Record<FormKind, string> = {
  diagnostic: 'Diagnóstico',
  gap_analysis: 'Gap Analysis',
  generic: 'Genérico',
};

const STATUS_LABELS: Record<TemplateStatus, string> = {
  draft: 'Rascunho',
  active: 'Ativo',
  archived: 'Arquivado',
};

const STATUS_SEVERITY: Record<TemplateStatus, 'secondary' | 'success' | 'danger'> = {
  draft: 'secondary',
  active: 'success',
  archived: 'danger',
};

type FieldType = FormField['type'];

/** Campo no editor: estende FormField com um texto auxiliar p/ editar as opções do tipo seleção. */
interface EditorField extends FormField {
  _optionsText?: string;
}

const FIELD_TYPES: { label: string; value: FieldType }[] = [
  { label: 'Texto', value: 'text' },
  { label: 'Texto longo', value: 'textarea' },
  { label: 'Sim/Não', value: 'boolean' },
  { label: 'Número', value: 'number' },
  { label: 'Seleção', value: 'select' },
];

const KIND_OPTIONS: { label: string; value: FormKind }[] = [
  { label: 'Diagnóstico', value: 'diagnostic' },
  { label: 'Gap Analysis', value: 'gap_analysis' },
  { label: 'Genérico', value: 'generic' },
];

@Component({
  selector: 'app-form-templates',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CardModule, ButtonModule, SelectModule, TagModule, RouterLink],
  template: `
    <div class="page-header">
      <h2>Templates de Formulário</h2>
      <p-button label="Novo template" icon="pi pi-plus" (onClick)="openNew()" />
    </div>

    @if (loading()) {
      <p class="hint">Carregando...</p>
    } @else if (templates().length === 0 && !editing()) {
      <p class="empty">Nenhum template criado ainda.</p>
    }

    @if (editing()) {
      <p-card class="editor">
        <h3>{{ editId() ? 'Editar template' : 'Novo template' }}</h3>
        <div class="form-row">
          <label>Título</label>
          <input type="text" [(ngModel)]="editTitle" placeholder="Ex.: Diagnóstico de Contexto" />
        </div>
        <div class="form-row">
          <label>Tipo</label>
          <p-select [options]="kindOptions" optionLabel="label" optionValue="value" [(ngModel)]="editKind" />
        </div>

        <h4>Campos</h4>
        @if (editFields().length === 0) {
          <p class="empty small">Nenhum campo. Clique em "Adicionar campo".</p>
        }
        @for (f of editFields(); track $index) {
          <div class="field-card">
            <div class="fc-row">
              <div class="fc-col grow">
                <label>Pergunta / Rótulo</label>
                <input type="text" [(ngModel)]="f.label" placeholder="Ex.: Razão social" (blur)="autoKey(f)" />
              </div>
              <div class="fc-col">
                <label>Tipo</label>
                <p-select [options]="fieldTypes" optionLabel="label" optionValue="value" [(ngModel)]="f.type" />
              </div>
              <div class="fc-col req">
                <label>Obrigatório</label>
                <input type="checkbox" [(ngModel)]="f.required" />
              </div>
              <button type="button" class="rm" (click)="removeField($index)" title="Remover campo">✕</button>
            </div>

            <div class="fc-row">
              <div class="fc-col">
                <label>Código (chave)</label>
                <input type="text" [(ngModel)]="f.key" placeholder="chave_campo" />
              </div>
              <div class="fc-col">
                <label>Seção</label>
                <input type="text" [(ngModel)]="f.section" placeholder="Ex.: Dados da organização" />
              </div>
              <div class="fc-col narrow">
                <label>Ordem</label>
                <input type="number" [(ngModel)]="f.order" />
              </div>
              @if (f.type === 'text') {
                <div class="fc-col">
                  <label>Máscara</label>
                  <input type="text" [(ngModel)]="f.mask" placeholder="999.999.999-99" />
                </div>
              }
            </div>

            <div class="fc-row">
              <div class="fc-col grow">
                <label>Texto de ajuda (opcional)</label>
                <input type="text" [(ngModel)]="f.help_text" placeholder="Instrução exibida abaixo do campo" />
              </div>
            </div>

            @if (f.type === 'select') {
              <div class="fc-row">
                <div class="fc-col grow">
                  <label>Opções (separadas por vírgula)</label>
                  <input type="text" [(ngModel)]="f._optionsText" placeholder="Opção A, Opção B, Opção C" />
                </div>
              </div>
            }
          </div>
        }

        <div class="actions">
          <p-button label="Adicionar campo" severity="secondary" size="small" (onClick)="addField()" />
        </div>

        <div class="actions footer">
          <p-button label="Salvar" (onClick)="save()" [disabled]="saving()" />
          <p-button label="Cancelar" severity="secondary" (onClick)="cancelEdit()" />
        </div>
      </p-card>
    }

    <div class="template-list">
      @for (t of templates(); track t.id) {
        <p-card class="tpl-card">
          <div class="tpl-header">
            <span class="tpl-title">{{ t.title }}</span>
            <p-tag [value]="statusLabel(t.status)" [severity]="statusSeverity(t.status)" />
            <span class="tpl-kind">{{ kindLabel(t.kind) }}</span>
          </div>
          <p class="tpl-fields">{{ t.schema.length }} campo(s)</p>
          <div class="tpl-actions">
            <p-button label="Editar" severity="secondary" size="small" (onClick)="openEdit(t)" />
            @if (t.status === 'archived') {
              <p-button label="Desarquivar" severity="success" size="small" (onClick)="setStatus(t, 'active')" />
            } @else {
              <p-button label="Arquivar" severity="danger" size="small" (onClick)="setStatus(t, 'archived')" />
            }
            @if (t.status !== 'archived') {
              <a [routerLink]="['/app', 'form-assignments']" [queryParams]="{ template_id: t.id }"
                class="assign-link">Atribuir →</a>
            }
          </div>
        </p-card>
      }
    </div>
  `,
  styles: `
    .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
    h2 { margin: 0; }
    .hint, .empty { opacity: 0.7; font-style: italic; }
    .empty.small { font-size: 0.85rem; margin: 0.5rem 0; }
    .editor { margin-bottom: 1.5rem; }
    h3, h4 { margin-top: 0; }
    .form-row { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
    .form-row label { font-size: 0.85rem; font-weight: 600; opacity: 0.8; }
    /* Editor de campo (card) */
    .field-card {
      border: 1px solid var(--p-content-border-color, #3a3a3a); border-radius: 8px;
      padding: 0.75rem; margin-bottom: 0.75rem;
      background: var(--p-surface-hover, rgba(255,255,255,.02));
    }
    .fc-row { display: flex; gap: 0.6rem; align-items: flex-end; margin-bottom: 0.5rem; }
    .fc-row:last-child { margin-bottom: 0; }
    .fc-col { display: flex; flex-direction: column; gap: 0.2rem; flex: 1 1 0; min-width: 0; }
    .fc-col.grow { flex: 3 1 0; }
    .fc-col.narrow { flex: 0 0 5rem; }
    .fc-col.req { flex: 0 0 5.5rem; align-items: flex-start; }
    .fc-col label { font-size: 0.78rem; font-weight: 600; opacity: 0.7; }
    input[type='text'], input[type='number'] {
      width: 100%; background: var(--p-content-background, #1e1e1e);
      border: 1px solid var(--p-content-border-color, #444); border-radius: 6px;
      padding: 0.4rem 0.5rem; font: inherit; color: inherit;
    }
    input[type='checkbox'] { width: 1.1rem; height: 1.1rem; }
    .req input[type='checkbox'] { margin-top: 0.4rem; }
    .rm {
      background: transparent; border: none; color: #f08a8a; cursor: pointer;
      padding: 0.3rem 0.45rem; font: inherit; font-size: 1rem; align-self: flex-end;
    }
    .rm:hover { color: #ff6b6b; }
    .actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
    .actions.footer { border-top: 1px solid var(--p-content-border-color, #333); padding-top: 0.75rem; margin-top: 1rem; }
    .template-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .tpl-card { cursor: default; }
    .tpl-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.25rem; }
    .tpl-title { font-weight: 600; flex: 1; }
    .tpl-kind { font-size: 0.82rem; opacity: 0.7; }
    .tpl-fields { margin: 0 0 0.5rem; font-size: 0.85rem; opacity: 0.7; }
    .tpl-actions { display: flex; gap: 0.5rem; align-items: center; }
    .assign-link { font-size: 0.85rem; color: var(--p-primary-color, #6c63ff); text-decoration: none; margin-left: auto; }
    .assign-link:hover { text-decoration: underline; }
  `,
})
export class FormTemplatesPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  protected readonly templates = signal<FormTemplate[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly editing = signal(false);
  protected readonly editId = signal<string | null>(null);
  protected readonly editFields = signal<EditorField[]>([]);

  protected editTitle = '';
  protected editKind: FormKind = 'diagnostic';

  protected readonly kindOptions = KIND_OPTIONS;
  protected readonly fieldTypes = FIELD_TYPES;

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.api.listTemplates().subscribe({
      next: (list) => { this.templates.set(list); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  protected kindLabel(k: FormKind): string { return KIND_LABELS[k]; }
  protected statusLabel(s: TemplateStatus): string { return STATUS_LABELS[s]; }
  protected statusSeverity(s: TemplateStatus) { return STATUS_SEVERITY[s]; }

  protected openNew(): void {
    this.editId.set(null);
    this.editTitle = '';
    this.editKind = 'diagnostic';
    this.editFields.set([]);
    this.editing.set(true);
  }

  protected openEdit(t: FormTemplate): void {
    this.editId.set(t.id);
    this.editTitle = t.title;
    this.editKind = t.kind;
    this.editFields.set(
      t.schema.map((f) => ({ ...f, _optionsText: (f.options ?? []).join(', ') })),
    );
    this.editing.set(true);
  }

  protected cancelEdit(): void { this.editing.set(false); }

  protected addField(): void {
    const nextOrder = this.editFields().length;
    this.editFields.update((list) => [
      ...list,
      { label: '', key: '', type: 'text', required: false, order: nextOrder, _optionsText: '' },
    ]);
  }

  protected removeField(i: number): void {
    this.editFields.update((list) => list.filter((_, idx) => idx !== i));
  }

  protected autoKey(f: EditorField): void {
    if (!f.key && f.label) {
      f.key = f.label
        .toLowerCase()
        .normalize('NFD')
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '');
    }
  }

  /** Limpa o campo p/ persistência: aplica opções, remove vazios, normaliza ordem. */
  private toFormField(f: EditorField, index: number): FormField {
    const out: FormField = {
      label: f.label,
      key: f.key,
      type: f.type,
      required: !!f.required,
      order: f.order ?? index,
    };
    if (f.section?.trim()) out.section = f.section.trim();
    if (f.help_text?.trim()) out.help_text = f.help_text.trim();
    if (f.type === 'text' && f.mask?.trim()) out.mask = f.mask.trim();
    if (f.type === 'select') {
      out.options = (f._optionsText ?? '')
        .split(',')
        .map((o) => o.trim())
        .filter((o) => o.length > 0);
    }
    return out;
  }

  protected save(): void {
    if (!this.editTitle.trim()) {
      this.messages.add({ severity: 'warn', summary: 'Título obrigatório', life: 3000 });
      return;
    }
    this.saving.set(true);
    const schema = this.editFields().map((f, i) => this.toFormField(f, i));
    const payload = { kind: this.editKind, title: this.editTitle, schema };
    const req = this.editId()
      ? this.api.updateTemplate(this.editId()!, payload)
      : this.api.createTemplate(payload);

    req.subscribe({
      next: () => {
        this.saving.set(false);
        this.editing.set(false);
        this.messages.add({ severity: 'success', summary: 'Template salvo', life: 3000 });
        this.load();
      },
      error: () => this.saving.set(false),
    });
  }

  protected setStatus(t: FormTemplate, status: TemplateStatus): void {
    this.api.updateTemplate(t.id, { status }).subscribe({
      next: () => {
        this.messages.add({
          severity: 'info',
          summary: status === 'archived' ? 'Template arquivado' : 'Template reativado',
          life: 3000,
        });
        this.load();
      },
    });
  }
}
