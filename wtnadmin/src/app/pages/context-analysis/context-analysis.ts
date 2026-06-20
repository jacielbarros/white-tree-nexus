import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { ContextAnalysis } from '@app/core/models';

@Component({
  selector: 'app-context-analysis-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FormsModule, CardModule, ButtonModule, InputTextModule, SelectModule, TableModule, TextareaModule],
  template: `
    <h2>Análise de Contexto</h2>
    <p-card styleClass="mb">
      <form [formGroup]="analysisForm" (ngSubmit)="saveAnalysis()" class="stack">
        <textarea pTextarea rows="4" formControlName="intended_outcomes" placeholder="Resultados pretendidos"></textarea>
        <textarea pTextarea rows="3" formControlName="methodology" placeholder="Metodologia/fontes"></textarea>
        <div class="actions">
          <p-button type="submit" label="Salvar" />
          <p-button label="Enviar para revisão" severity="secondary" (onClick)="submitReview()" />
          <p-button label="Aprovar" severity="success" (onClick)="approve()" />
        </div>
      </form>
    </p-card>

    <p-card header="Questões" styleClass="mb">
      <form [formGroup]="issueForm" (ngSubmit)="addIssue()" class="row-form">
        <p-select [options]="origins" formControlName="origin" />
        <p-select [options]="frameworks" formControlName="framework" />
        <input pInputText formControlName="category" placeholder="Categoria" />
        <input pInputText formControlName="description" placeholder="Descrição" />
        <p-select [options]="levels" formControlName="impact" />
        <p-button type="submit" label="Adicionar" />
      </form>
    </p-card>

    <p-table [value]="analysis()?.issues ?? []">
      <ng-template pTemplate="header"><tr><th>Origem</th><th>Framework</th><th>Categoria</th><th>Descrição</th><th>Impacto</th></tr></ng-template>
      <ng-template pTemplate="body" let-row><tr><td>{{ row.origin }}</td><td>{{ row.framework }}</td><td>{{ row.category }}</td><td>{{ row.description }}</td><td>{{ row.impact }}</td></tr></ng-template>
    </p-table>
  `,
  styles: `
    h2 { margin-top: 0; }
    .mb { display: block; margin-bottom: 1rem; }
    .stack { display: grid; gap: 0.75rem; }
    .row-form, .actions { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; }
    input { min-width: 12rem; }
  `,
})
export class ContextAnalysisPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly analysis = signal<ContextAnalysis | null>(null);
  protected readonly levels = ['alto', 'medio', 'baixo'];
  protected readonly origins = ['internal', 'external'];
  protected readonly frameworks = ['pestel', 'swot'];

  protected readonly analysisForm = this.fb.group({
    intended_outcomes: this.fb.control(''),
    methodology: this.fb.control(''),
  });
  protected readonly issueForm = this.fb.group({
    origin: this.fb.control<'internal' | 'external'>('external'),
    framework: this.fb.control<'pestel' | 'swot'>('pestel'),
    category: this.fb.control(''),
    description: this.fb.control(''),
    impact: this.fb.control<'alto' | 'medio' | 'baixo'>('alto'),
  });

  ngOnInit(): void { this.load(); }

  private load(): void {
    this.api.getContextAnalysis().subscribe({ next: (row) => {
      this.analysis.set(row);
      this.analysisForm.patchValue({ intended_outcomes: row.intended_outcomes, methodology: row.methodology ?? '' });
    } });
  }

  protected saveAnalysis(): void {
    this.api.saveContextAnalysis(this.analysisForm.getRawValue()).subscribe({ next: () => this.load() });
  }

  protected addIssue(): void {
    this.api.createContextIssue(this.issueForm.getRawValue()).subscribe({ next: () => this.load() });
  }

  protected submitReview(): void {
    this.api.submitContextAnalysis().subscribe({ next: () => this.load() });
  }

  protected approve(): void {
    this.api.approveContextAnalysis('uso_interno').subscribe({ next: () => this.load() });
  }
}
