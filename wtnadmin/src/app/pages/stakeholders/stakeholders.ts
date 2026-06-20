import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';

import { ApiService } from '@app/core/api.service';
import { StakeholderMap } from '@app/core/models';

@Component({
  selector: 'app-stakeholders-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FormsModule, CardModule, ButtonModule, InputTextModule, SelectModule, TableModule],
  template: `
    <h2>Partes Interessadas</h2>
    <p-card styleClass="mb">
      <form [formGroup]="form" (ngSubmit)="add()" class="row-form">
        <input pInputText formControlName="name" placeholder="Nome" />
        <p-select [options]="types" formControlName="type" />
        <p-select [options]="levels" formControlName="power" />
        <p-select [options]="levels" formControlName="interest" />
        <p-button type="submit" label="Adicionar" />
      </form>
    </p-card>
    <p-table [value]="map()?.stakeholders ?? []">
      <ng-template pTemplate="header"><tr><th>Nome</th><th>Tipo</th><th>Poder</th><th>Interesse</th><th>Estratégia</th></tr></ng-template>
      <ng-template pTemplate="body" let-row><tr><td>{{ row.name }}</td><td>{{ row.type }}</td><td>{{ row.power }}</td><td>{{ row.interest }}</td><td>{{ row.strategy }}</td></tr></ng-template>
    </p-table>
  `,
  styles: `
    h2 { margin-top: 0; }
    .mb { display: block; margin-bottom: 1rem; }
    .row-form { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
  `,
})
export class StakeholdersPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly map = signal<StakeholderMap | null>(null);
  protected readonly levels = ['alto', 'medio', 'baixo'];
  protected readonly types = ['internal', 'external'];
  protected readonly form = this.fb.group({
    name: this.fb.control(''),
    type: this.fb.control<'internal' | 'external'>('external'),
    power: this.fb.control<'alto' | 'medio' | 'baixo'>('alto'),
    interest: this.fb.control<'alto' | 'medio' | 'baixo'>('alto'),
  });

  ngOnInit(): void { this.load(); }
  private load(): void { this.api.getStakeholderMap().subscribe({ next: (row) => this.map.set(row) }); }
  protected add(): void { this.api.createStakeholder(this.form.getRawValue()).subscribe({ next: () => this.load() }); }
}
