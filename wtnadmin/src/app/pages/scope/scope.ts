import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { ScopeStatement } from '@app/core/models';

@Component({
  selector: 'app-scope-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FormsModule, CardModule, ButtonModule, InputTextModule, SelectModule, TableModule, TextareaModule],
  template: `
    <h2>Declaração de Escopo</h2>
    <p-card styleClass="mb">
      <form [formGroup]="scopeForm" (ngSubmit)="save()" class="stack">
        <textarea pTextarea rows="4" formControlName="interfaces_dependencies" placeholder="Interfaces e dependências"></textarea>
        <p-button type="submit" label="Salvar" />
      </form>
    </p-card>
    <p-card header="Itens" styleClass="mb">
      <form [formGroup]="itemForm" (ngSubmit)="addItem()" class="row-form">
        <p-select [options]="kinds" formControlName="kind" />
        <input pInputText formControlName="description" placeholder="Descrição" />
        <input pInputText formControlName="justification" placeholder="Justificativa" />
        <p-button type="submit" label="Adicionar" />
      </form>
    </p-card>
    <p-table [value]="scope()?.items ?? []">
      <ng-template pTemplate="header"><tr><th>Tipo</th><th>Descrição</th><th>Justificativa</th></tr></ng-template>
      <ng-template pTemplate="body" let-row><tr><td>{{ row.kind }}</td><td>{{ row.description }}</td><td>{{ row.justification }}</td></tr></ng-template>
    </p-table>
  `,
  styles: `
    h2 { margin-top: 0; }
    .mb { display: block; margin-bottom: 1rem; }
    .stack { display: grid; gap: 0.75rem; }
    .row-form { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
  `,
})
export class ScopePage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly scope = signal<ScopeStatement | null>(null);
  protected readonly kinds = ['inclusion', 'exclusion'];
  protected readonly scopeForm = this.fb.group({ interfaces_dependencies: this.fb.control('') });
  protected readonly itemForm = this.fb.group({
    kind: this.fb.control<'inclusion' | 'exclusion'>('inclusion'),
    description: this.fb.control(''),
    justification: this.fb.control(''),
  });

  ngOnInit(): void { this.load(); }
  private load(): void {
    this.api.getScope().subscribe({ next: (row) => { this.scope.set(row); this.scopeForm.patchValue({ interfaces_dependencies: row.interfaces_dependencies }); } });
  }
  protected save(): void { this.api.saveScope(this.scopeForm.getRawValue()).subscribe({ next: () => this.load() }); }
  protected addItem(): void { this.api.createScopeItem(this.itemForm.getRawValue()).subscribe({ next: () => this.load() }); }
}
