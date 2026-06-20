import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';

import { ApiService } from '@app/core/api.service';

type FieldType = 'text' | 'textarea' | 'boolean' | 'number';

interface DiagField {
  id: number;
  secao: string;
  rotulo: string;
  tipo: FieldType;
  valor: string | number | boolean;
}

/** Seções do diagnóstico-questionário (FR-002). */
const SECOES = [
  'Identificação',
  'Estrutura',
  'Negócio',
  'Tecnologia',
  'Dados tratados',
  'Cadeia de suprimento',
  'Requisitos',
];

const TIPOS: { label: string; value: FieldType }[] = [
  { label: 'Texto', value: 'text' },
  { label: 'Texto longo', value: 'textarea' },
  { label: 'Sim/Não', value: 'boolean' },
  { label: 'Número', value: 'number' },
];

@Component({
  selector: 'app-diagnostic-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CardModule, ButtonModule],
  template: `
    <h2>Diagnóstico</h2>
    <p-card>
      <p class="hint">
        Monte o questionário de contexto adicionando campos por seção. Os dados são salvos como
        rascunho e podem ser concluídos. (Em breve: enviar para o cliente/consultor responder.)
      </p>

      @if (fields().length) {
        <div class="grid head">
          <span>Seção</span><span>Rótulo / Pergunta</span><span>Tipo</span><span>Valor</span><span></span>
        </div>
        @for (f of fields(); track f.id) {
          <div class="grid row">
            <select [(ngModel)]="f.secao">
              @for (s of secoes; track s) { <option [value]="s">{{ s }}</option> }
            </select>
            <input type="text" [(ngModel)]="f.rotulo" placeholder="Ex.: A organização trata dados pessoais?" />
            <select [(ngModel)]="f.tipo" (ngModelChange)="onTipoChange(f)">
              @for (t of tipos; track t.value) { <option [value]="t.value">{{ t.label }}</option> }
            </select>
            <span class="val">
              @switch (f.tipo) {
                @case ('boolean') { <input type="checkbox" [(ngModel)]="f.valor" /> }
                @case ('number') { <input type="number" [(ngModel)]="f.valor" /> }
                @case ('textarea') { <textarea rows="2" [(ngModel)]="f.valor"></textarea> }
                @default { <input type="text" [(ngModel)]="f.valor" /> }
              }
            </span>
            <button type="button" class="rm" (click)="removeField(f.id)">Remover</button>
          </div>
        }
      } @else {
        <p class="empty">Nenhum campo ainda. Clique em "Adicionar campo" para começar.</p>
      }

      <div class="actions">
        <p-button label="Adicionar campo" severity="secondary" (onClick)="addField()" />
      </div>
      <div class="actions footer">
        <p-button label="Salvar rascunho" (onClick)="save('draft')" [disabled]="saving()" />
        <p-button label="Concluir" severity="secondary" (onClick)="save('completed')" [disabled]="saving()" />
      </div>
    </p-card>
  `,
  styles: `
    h2 { margin-top: 0; }
    .hint { opacity: 0.8; font-size: 0.9rem; margin-top: 0; }
    .empty { opacity: 0.7; font-style: italic; }
    .grid {
      display: grid;
      grid-template-columns: 1.2fr 2.2fr 1fr 1.6fr auto;
      gap: 0.5rem; align-items: center;
    }
    .grid.head { font-weight: 600; opacity: 0.7; padding: 0.25rem 0; font-size: 0.85rem; }
    .grid.row { padding: 0.3rem 0; }
    select, input[type='text'], input[type='number'], textarea {
      width: 100%; color: inherit;
      background: var(--p-content-background, #1e1e1e);
      border: 1px solid var(--p-content-border-color, #444);
      border-radius: 6px; padding: 0.45rem 0.55rem; font: inherit;
    }
    input[type='checkbox'] { width: 1.15rem; height: 1.15rem; }
    .rm {
      background: transparent; border: none; color: #f08a8a; cursor: pointer;
      padding: 0.25rem 0.4rem; font: inherit;
    }
    .rm:hover { text-decoration: underline; }
    .actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
    .actions.footer { border-top: 1px solid var(--p-content-border-color, #333); padding-top: 1rem; }
  `,
})
export class DiagnosticPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);
  protected readonly saving = signal(false);
  protected readonly secoes = SECOES;
  protected readonly tipos = TIPOS;
  private seq = 0;

  protected readonly fields = signal<DiagField[]>([
    { id: this.nextId(), secao: 'Identificação', rotulo: 'Razão social', tipo: 'text', valor: '' },
    { id: this.nextId(), secao: 'Negócio', rotulo: 'Setor de atuação', tipo: 'text', valor: '' },
    {
      id: this.nextId(),
      secao: 'Dados tratados',
      rotulo: 'A organização trata dados pessoais?',
      tipo: 'boolean',
      valor: false,
    },
  ]);

  ngOnInit(): void {
    this.api.getDiagnostic().subscribe({
      next: (diagnostic) => {
        const campos = (diagnostic.sections as { campos?: unknown })?.campos;
        if (Array.isArray(campos) && campos.length) {
          this.fields.set(campos.map((c) => this.fromStored(c as Record<string, unknown>)));
        }
      },
    });
  }

  protected addField(): void {
    this.fields.update((list) => [
      ...list,
      { id: this.nextId(), secao: this.secoes[0], rotulo: '', tipo: 'text', valor: '' },
    ]);
  }

  protected removeField(id: number): void {
    this.fields.update((list) => list.filter((f) => f.id !== id));
  }

  protected onTipoChange(f: DiagField): void {
    f.valor = f.tipo === 'boolean' ? false : f.tipo === 'number' ? 0 : '';
  }

  protected save(status: 'draft' | 'completed'): void {
    this.saving.set(true);
    const campos = this.fields().map((f) => ({
      secao: f.secao,
      rotulo: f.rotulo,
      chave: this.slug(f.rotulo),
      tipo: f.tipo,
      valor: f.valor,
    }));
    this.api.saveDiagnostic({ status, sections: { versao_form: 1, campos } }).subscribe({
      next: () => {
        this.saving.set(false);
        this.messages.add({
          severity: 'success',
          summary: 'Diagnóstico salvo',
          detail: status === 'completed' ? 'Marcado como concluído.' : 'Rascunho salvo.',
          life: 3000,
        });
      },
      error: () => this.saving.set(false),
    });
  }

  private fromStored(c: Record<string, unknown>): DiagField {
    const tipo = (TIPOS.find((t) => t.value === c['tipo'])?.value ?? 'text') as FieldType;
    return {
      id: this.nextId(),
      secao: typeof c['secao'] === 'string' ? (c['secao'] as string) : this.secoes[0],
      rotulo: typeof c['rotulo'] === 'string' ? (c['rotulo'] as string) : '',
      tipo,
      valor: (c['valor'] as string | number | boolean) ?? (tipo === 'boolean' ? false : ''),
    };
  }

  private slug(label: string): string {
    return label
      .toLowerCase()
      .normalize('NFD')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  }

  private nextId(): number {
    return ++this.seq;
  }
}
