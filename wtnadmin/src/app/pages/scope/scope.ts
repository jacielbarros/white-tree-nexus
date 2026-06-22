import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';
import { ScopeStatement } from '@app/core/models';

const STATUS: Record<string, { label: string; cls: string }> = {
  draft: { label: 'Rascunho', cls: 'wtn-tag--neutral' },
  in_review: { label: 'Em revisão', cls: 'wtn-tag--info' },
  in_force: { label: 'Em vigor', cls: 'wtn-tag--success' },
};

@Component({
  selector: 'app-scope-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Declaração de Escopo</h1>
        <p class="wtn-page-desc">Cláusula 4.3 · limites e aplicabilidade do SGSI.</p>
      </div>
    </header>

    <section class="wtn-card scope-card">
      <div class="card-head">
        <span class="card-title">Interfaces e dependências</span>
        <span class="wtn-tag {{ statusView().cls }}">{{ statusView().label }}</span>
      </div>
      <form [formGroup]="scopeForm" (ngSubmit)="save()" class="field-stack">
        <textarea
          class="wtn-field-input"
          rows="4"
          formControlName="interfaces_dependencies"
          placeholder="Descreva interfaces e dependências (processos, fornecedores, sistemas) relevantes ao escopo."
        ></textarea>
        <div>
          <button type="submit" class="wtn-btn-primary" [disabled]="saving()">
            {{ saving() ? 'Salvando…' : 'Salvar' }}
          </button>
        </div>
      </form>
    </section>

    <section class="wtn-card scope-card">
      <div class="card-head">
        <span class="card-title">Itens de escopo</span>
      </div>
      <form [formGroup]="itemForm" (ngSubmit)="addItem()" class="item-form">
        <select class="wtn-field-input" formControlName="kind">
          <option value="inclusion">Inclusão</option>
          <option value="exclusion">Exclusão</option>
        </select>
        <input class="wtn-field-input" formControlName="description" placeholder="Descrição" />
        <input class="wtn-field-input" formControlName="justification" placeholder="Justificativa" />
        <button type="submit" class="wtn-btn-primary" [disabled]="adding()">Adicionar</button>
      </form>

      @if ((scope()?.items ?? []).length === 0) {
        <div class="items-empty">Nenhum item de escopo definido ainda.</div>
      } @else {
        <table class="scope-table">
          <thead>
            <tr><th class="col-kind">Tipo</th><th>Descrição</th><th>Justificativa</th></tr>
          </thead>
          <tbody>
            @for (row of scope()!.items; track row.id) {
              <tr>
                <td>
                  <span class="wtn-tag {{ row.kind === 'inclusion' ? 'wtn-tag--success' : 'wtn-tag--neutral' }}">
                    {{ row.kind === 'inclusion' ? 'Inclusão' : 'Exclusão' }}
                  </span>
                </td>
                <td>{{ row.description }}</td>
                <td class="muted-cell">{{ row.justification || '—' }}</td>
              </tr>
            }
          </tbody>
        </table>
      }
    </section>
  `,
  styles: `
    :host { display: block; }

    .scope-card {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      margin-bottom: 16px;
      padding: 20px;
    }

    .card-head {
      align-items: center;
      display: flex;
      gap: 10px;
      justify-content: space-between;
      margin-bottom: 14px;
    }

    .card-title {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 600;
    }

    .field-stack {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .wtn-field-input {
      background: var(--wtn-surface);
      border: 1px solid var(--wtn-border-strong);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-text);
      font: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      width: 100%;
    }

    textarea.wtn-field-input { resize: vertical; }

    .wtn-field-input:focus {
      border-color: var(--wtn-focus);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--wtn-focus) 26%, transparent);
      outline: 0;
    }

    .wtn-btn-primary {
      background: var(--wtn-primary);
      border: 0;
      border-radius: var(--wtn-r-md);
      color: var(--wtn-primary-contrast);
      cursor: pointer;
      font: inherit;
      font-size: 13px;
      font-weight: 600;
      padding: 9px 18px;
      white-space: nowrap;
    }

    .wtn-btn-primary:hover:not(:disabled) { background: var(--wtn-primary-hover); }
    .wtn-btn-primary:disabled { cursor: not-allowed; opacity: .6; }

    .item-form {
      align-items: center;
      display: grid;
      gap: 10px;
      grid-template-columns: 150px 1fr 1fr auto;
      margin-bottom: 16px;
    }

    .scope-table {
      border-collapse: collapse;
      font-size: 13px;
      width: 100%;
    }

    .scope-table th {
      border-bottom: 1px solid var(--wtn-border);
      color: var(--wtn-muted);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: .06em;
      padding: 8px 10px;
      text-align: left;
      text-transform: uppercase;
    }

    .scope-table td {
      border-bottom: 1px solid var(--wtn-surface-2);
      color: var(--wtn-text);
      padding: 10px;
      vertical-align: middle;
    }

    .col-kind { width: 130px; }
    .muted-cell { color: var(--wtn-text-2); }

    .items-empty {
      color: var(--wtn-text-2);
      font-size: 13px;
      padding: 8px 0;
    }

    @media (max-width: 760px) {
      .item-form { grid-template-columns: 1fr; }
    }
  `,
})
export class ScopePage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly messages = inject(MessageService);

  protected readonly scope = signal<ScopeStatement | null>(null);
  protected readonly saving = signal(false);
  protected readonly adding = signal(false);

  protected readonly statusView = computed(
    () => STATUS[this.scope()?.draft_status ?? 'draft'] ?? STATUS['draft'],
  );

  protected readonly scopeForm = this.fb.group({ interfaces_dependencies: this.fb.control('') });
  protected readonly itemForm = this.fb.group({
    kind: this.fb.control<'inclusion' | 'exclusion'>('inclusion'),
    description: this.fb.control(''),
    justification: this.fb.control(''),
  });

  ngOnInit(): void {
    this.load();
  }

  protected save(): void {
    this.saving.set(true);
    this.api.saveScope(this.scopeForm.getRawValue()).subscribe({
      next: () => {
        this.messages.add({ severity: 'success', summary: 'Escopo salvo', life: 2500 });
        this.saving.set(false);
        this.load();
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  protected addItem(): void {
    if (!this.itemForm.value.description?.trim()) {
      this.messages.add({ severity: 'warn', summary: 'Descrição obrigatória' });
      return;
    }
    this.adding.set(true);
    this.api.createScopeItem(this.itemForm.getRawValue()).subscribe({
      next: () => {
        this.itemForm.patchValue({ description: '', justification: '' });
        this.adding.set(false);
        this.load();
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.adding.set(false);
      },
    });
  }

  private load(): void {
    this.api.getScope().subscribe({
      next: (row) => {
        this.scope.set(row);
        this.scopeForm.patchValue({ interfaces_dependencies: row.interfaces_dependencies });
      },
    });
  }
}
