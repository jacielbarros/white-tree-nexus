import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TableModule } from 'primeng/table';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { ContextAnalysis, ContextIssue, Level } from '@app/core/models';

type IssueOrigin = 'internal' | 'external';
type IssueFramework = 'pestel' | 'swot';
type IssueNature = 'contextual' | 'strength' | 'weakness' | 'opportunity' | 'threat';

interface Option<T extends string> {
  label: string;
  value: T;
}

interface IssuePreset {
  label: string;
  value: string;
  origin: IssueOrigin;
  framework: IssueFramework;
  nature: IssueNature;
  category: string;
  description: string;
  impact: Level;
}

const ORIGIN_OPTIONS: Option<IssueOrigin>[] = [
  { label: 'Externa', value: 'external' },
  { label: 'Interna', value: 'internal' },
];

const FRAMEWORK_OPTIONS: Option<IssueFramework>[] = [
  { label: 'PESTEL', value: 'pestel' },
  { label: 'SWOT', value: 'swot' },
];

const IMPACT_OPTIONS: Option<Level>[] = [
  { label: 'Alto', value: 'alto' },
  { label: 'Medio', value: 'medio' },
  { label: 'Baixo', value: 'baixo' },
];

const EXTERNAL_NATURE_OPTIONS: Option<IssueNature>[] = [
  { label: 'Questao contextual', value: 'contextual' },
  { label: 'Oportunidade', value: 'opportunity' },
  { label: 'Ameaca', value: 'threat' },
];

const INTERNAL_NATURE_OPTIONS: Option<IssueNature>[] = [
  { label: 'Questao contextual', value: 'contextual' },
  { label: 'Forca', value: 'strength' },
  { label: 'Fraqueza', value: 'weakness' },
];

const ISSUE_PRESETS: IssuePreset[] = [
  {
    label: 'PESTEL > Dimensao Politica',
    value: 'pestel-politica',
    origin: 'external',
    framework: 'pestel',
    nature: 'threat',
    category: 'Politica',
    description: 'Mudancas em governanca digital, fiscalizacao ou atuacao de autoridades podem afetar prioridades e obrigacoes do SGSI.',
    impact: 'medio',
  },
  {
    label: 'PESTEL > Dimensao Economica',
    value: 'pestel-economica',
    origin: 'external',
    framework: 'pestel',
    nature: 'contextual',
    category: 'Economica',
    description: 'Custos de nuvem, credito, cambio ou investimento podem afetar orcamento, capacidade e sustentacao das iniciativas de seguranca.',
    impact: 'medio',
  },
  {
    label: 'PESTEL > Dimensao Social',
    value: 'pestel-social',
    origin: 'external',
    framework: 'pestel',
    nature: 'contextual',
    category: 'Social',
    description: 'Trabalho remoto, privacidade e expectativa de transparencia em incidentes influenciam controles de pessoas, comunicacao e continuidade.',
    impact: 'medio',
  },
  {
    label: 'PESTEL > Dimensao Tecnologica',
    value: 'pestel-tecnologica',
    origin: 'external',
    framework: 'pestel',
    nature: 'threat',
    category: 'Tecnologica',
    description: 'Ameacas a SaaS, nuvem, IA, phishing e dependencias de software exigem controles tecnicos, monitoramento e resposta.',
    impact: 'alto',
  },
  {
    label: 'PESTEL > Dimensao Ambiental',
    value: 'pestel-ambiental',
    origin: 'external',
    framework: 'pestel',
    nature: 'threat',
    category: 'Ambiental',
    description: 'Eventos extremos e dependencia de infraestrutura podem afetar colaboradores remotos, disponibilidade e planos de continuidade.',
    impact: 'medio',
  },
  {
    label: 'PESTEL > Dimensao Legal',
    value: 'pestel-legal',
    origin: 'external',
    framework: 'pestel',
    nature: 'threat',
    category: 'Legal',
    description: 'LGPD, Marco Civil, regulacoes setoriais e contratos exigem controles, evidencias, retencao de registros e resposta a incidentes.',
    impact: 'alto',
  },
  {
    label: 'Interno > Valores',
    value: 'interno-valores',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Valores',
    description: 'Valores e cultura organizacional podem facilitar ou dificultar a adesao aos controles e praticas do SGSI.',
    impact: 'medio',
  },
  {
    label: 'Interno > Governanca',
    value: 'interno-governanca',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Governanca',
    description: 'Estrutura, patrocinio executivo, responsabilidades e governanca documental afetam a capacidade de aprovar, manter e auditar o SGSI.',
    impact: 'alto',
  },
  {
    label: 'Interno > Estrategia',
    value: 'interno-estrategia',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Estrategia',
    description: 'Objetivos estrategicos, ritmo de crescimento e prioridades de negocio podem alinhar ou tensionar a implantacao do SGSI.',
    impact: 'alto',
  },
  {
    label: 'Interno > Cultura',
    value: 'interno-cultura',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Cultura',
    description: 'Autonomia, canais internos e habitos de compartilhamento impactam classificacao da informacao, conscientizacao e execucao dos controles.',
    impact: 'alto',
  },
  {
    label: 'Interno > Recursos',
    value: 'interno-recursos',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Recursos',
    description: 'Orcamento, equipe, consultoria e capacidades tecnicas condicionam velocidade, qualidade e sustentabilidade do SGSI.',
    impact: 'medio',
  },
  {
    label: 'Interno > Sistemas e fluxos',
    value: 'interno-sistemas',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Sistemas',
    description: 'Arquitetura, SSO, cofre de senhas, inventario, CI/CD e fluxos de informacao determinam exposicoes e controles prioritarios.',
    impact: 'alto',
  },
  {
    label: 'Interno > Relacoes contratuais',
    value: 'interno-relacoes',
    origin: 'internal',
    framework: 'swot',
    nature: 'contextual',
    category: 'Relacoes',
    description: 'Contratos, NDAs, confidencialidade, fornecedores e foruns internos definem responsabilidades e evidencias esperadas.',
    impact: 'medio',
  },
];

const ORIGIN_LABEL: Record<IssueOrigin, string> = {
  external: 'Externa',
  internal: 'Interna',
};

const FRAMEWORK_LABEL: Record<IssueFramework, string> = {
  pestel: 'PESTEL',
  swot: 'SWOT',
};

const NATURE_LABEL: Record<IssueNature, string> = {
  contextual: 'Contextual',
  strength: 'Forca',
  weakness: 'Fraqueza',
  opportunity: 'Oportunidade',
  threat: 'Ameaca',
};

const IMPACT_LABEL: Record<Level, string> = {
  alto: 'Alto',
  medio: 'Medio',
  baixo: 'Baixo',
};

@Component({
  selector: 'app-context-analysis-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FormsModule, CardModule, ButtonModule, InputTextModule, SelectModule, TableModule, TextareaModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Analise de Contexto</h1>
        <p class="wtn-page-desc">Registre fatores internos e externos que influenciam o SGSI.</p>
      </div>
    </header>

    <p-card styleClass="mb">
      <form [formGroup]="analysisForm" (ngSubmit)="saveAnalysis()" class="stack">
        <textarea pTextarea rows="4" formControlName="intended_outcomes" placeholder="Resultados pretendidos"></textarea>
        <textarea pTextarea rows="3" formControlName="methodology" placeholder="Metodologia/fontes"></textarea>
        <div class="actions">
          <p-button type="submit" label="Salvar" icon="pi pi-save" />
          <p-button label="Enviar para revisao" icon="pi pi-send" severity="secondary" (onClick)="submitReview()" />
          <p-button label="Aprovar" icon="pi pi-check" severity="success" (onClick)="approve()" />
        </div>
      </form>
    </p-card>

    <p-card header="Questoes" styleClass="mb">
      <form [formGroup]="issueForm" (ngSubmit)="addIssue()" class="issue-form">
        <p-select
          class="preset-select"
          [options]="presetOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Modelo de questao"
          (onChange)="applyPreset($event.value)"
        />
        <p-select [options]="originOptions" optionLabel="label" optionValue="value" formControlName="origin" (onChange)="syncFramework()" />
        <p-select [options]="frameworkOptions" optionLabel="label" optionValue="value" formControlName="framework" (onChange)="syncOrigin()" />
        <p-select [options]="natureOptions()" optionLabel="label" optionValue="value" formControlName="nature" />
        <input pInputText formControlName="category" placeholder="Categoria" />
        <input pInputText class="description-input" formControlName="description" placeholder="Descricao" />
        <p-select [options]="impactOptions" optionLabel="label" optionValue="value" formControlName="impact" />
        <p-button type="submit" label="Adicionar" icon="pi pi-plus" />
      </form>
    </p-card>

    <p-table [value]="analysis()?.issues ?? []" styleClass="context-issues-table">
      <ng-template pTemplate="header">
        <tr>
          <th>Origem</th>
          <th>Framework</th>
          <th>Natureza</th>
          <th>Categoria</th>
          <th>Descricao</th>
          <th>Impacto</th>
          <th class="actions-col">Acoes</th>
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-row>
        <tr>
          <td>{{ originLabel(row) }}</td>
          <td>{{ frameworkLabel(row) }}</td>
          <td>{{ natureLabel(row) }}</td>
          <td>{{ row.category }}</td>
          <td>{{ row.description }}</td>
          <td><span class="impact-pill">{{ impactLabel(row) }}</span></td>
          <td class="actions-col">
            <p-button
              label="Excluir"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              [text]="true"
              ariaLabel="Excluir questao"
              (onClick)="deleteIssue(row.id)"
            />
          </td>
        </tr>
      </ng-template>
      <ng-template pTemplate="emptymessage">
        <tr>
          <td colspan="7" class="empty-state">Nenhuma questao registrada ainda.</td>
        </tr>
      </ng-template>
    </p-table>
  `,
  styles: `
    :host { display: block; }

    .mb { display: block; margin-bottom: 1rem; }
    .stack { display: grid; gap: 0.75rem; }

    .actions {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .issue-form {
      display: grid;
      grid-template-columns: minmax(220px, 1.2fr) minmax(120px, .6fr) minmax(120px, .6fr) minmax(150px, .8fr) minmax(150px, .9fr) minmax(220px, 1.4fr) minmax(110px, .6fr) auto;
      gap: 0.75rem;
      align-items: center;
    }

    .description-input { min-width: 16rem; }

    .actions-col {
      width: 112px;
      text-align: right;
      white-space: nowrap;
    }

    .impact-pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 10px;
      border-radius: 999px;
      background: var(--wtn-surface-2);
      color: var(--wtn-text-2);
      font-size: 12px;
      font-weight: 600;
    }

    .empty-state {
      padding: 1rem;
      color: var(--wtn-muted);
      text-align: center;
    }

    @media (max-width: 1200px) {
      .issue-form {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }

    @media (max-width: 760px) {
      .issue-form {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class ContextAnalysisPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly analysis = signal<ContextAnalysis | null>(null);
  protected readonly originOptions = ORIGIN_OPTIONS;
  protected readonly frameworkOptions = FRAMEWORK_OPTIONS;
  protected readonly impactOptions = IMPACT_OPTIONS;
  protected readonly presetOptions = ISSUE_PRESETS.map(({ label, value }) => ({ label, value }));

  protected readonly analysisForm = this.fb.group({
    intended_outcomes: this.fb.control(''),
    methodology: this.fb.control(''),
  });
  protected readonly issueForm = this.fb.group({
    origin: this.fb.control<IssueOrigin>('external'),
    framework: this.fb.control<IssueFramework>('pestel'),
    nature: this.fb.control<IssueNature>('contextual'),
    category: this.fb.control(''),
    description: this.fb.control(''),
    impact: this.fb.control<Level>('alto'),
  });

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.api.getContextAnalysis().subscribe({
      next: (row) => {
        this.analysis.set(row);
        this.analysisForm.patchValue({ intended_outcomes: row.intended_outcomes, methodology: row.methodology ?? '' });
      },
    });
  }

  protected saveAnalysis(): void {
    this.api.saveContextAnalysis(this.analysisForm.getRawValue()).subscribe({ next: () => this.load() });
  }

  protected addIssue(): void {
    this.api.createContextIssue(this.issueForm.getRawValue()).subscribe({
      next: () => {
        this.issueForm.patchValue({ description: '' });
        this.load();
      },
    });
  }

  protected deleteIssue(id: string): void {
    if (!globalThis.confirm('Excluir esta questao da analise de contexto?')) {
      return;
    }
    this.api.deleteContextIssue(id).subscribe({ next: () => this.load() });
  }

  protected applyPreset(value: string | null): void {
    const preset = ISSUE_PRESETS.find((item) => item.value === value);
    if (!preset) {
      return;
    }
    this.issueForm.patchValue({
      origin: preset.origin,
      framework: preset.framework,
      nature: preset.nature,
      category: preset.category,
      description: preset.description,
      impact: preset.impact,
    });
  }

  protected syncFramework(): void {
    const origin = this.issueForm.controls.origin.value;
    this.issueForm.controls.framework.setValue(origin === 'external' ? 'pestel' : 'swot');
    this.normalizeNatureForOrigin(origin);
  }

  protected syncOrigin(): void {
    const framework = this.issueForm.controls.framework.value;
    const origin = framework === 'pestel' ? 'external' : 'internal';
    this.issueForm.controls.origin.setValue(origin);
    this.normalizeNatureForOrigin(origin);
  }

  protected natureOptions(): Option<IssueNature>[] {
    return this.issueForm.controls.origin.value === 'external' ? EXTERNAL_NATURE_OPTIONS : INTERNAL_NATURE_OPTIONS;
  }

  private normalizeNatureForOrigin(origin: IssueOrigin): void {
    const nature = this.issueForm.controls.nature.value;
    if (origin === 'external' && (nature === 'strength' || nature === 'weakness')) {
      this.issueForm.controls.nature.setValue('contextual');
    }
    if (origin === 'internal' && (nature === 'opportunity' || nature === 'threat')) {
      this.issueForm.controls.nature.setValue('contextual');
    }
  }

  protected submitReview(): void {
    this.api.submitContextAnalysis().subscribe({ next: () => this.load() });
  }

  protected approve(): void {
    this.api.approveContextAnalysis('uso_interno').subscribe({ next: () => this.load() });
  }

  protected originLabel(row: ContextIssue): string {
    return ORIGIN_LABEL[row.origin];
  }

  protected frameworkLabel(row: ContextIssue): string {
    return FRAMEWORK_LABEL[row.framework];
  }

  protected natureLabel(row: ContextIssue): string {
    return NATURE_LABEL[row.nature ?? 'contextual'];
  }

  protected impactLabel(row: ContextIssue): string {
    return IMPACT_LABEL[row.impact];
  }
}
