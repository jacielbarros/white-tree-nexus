import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiService } from '@app/core/api.service';
import { AssignmentStatus, Diagnostic, FormAssignment, FormTemplate } from '@app/core/models';

interface IntakeView {
  source: string;
  assignmentId: string | null;
  completedAt: string | null;
  answers: { key: string; value: string }[];
}

const ASSIGNMENT_STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em preenchimento',
  submitted: 'Preenchido',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

const ASSIGNMENT_STATUS_CLASS: Record<AssignmentStatus, string> = {
  pending: 'wtn-tag--neutral',
  in_progress: 'wtn-tag--info',
  submitted: 'wtn-tag--info',
  signed: 'wtn-tag--success',
  completed: 'wtn-tag--success',
  cancelled: 'wtn-tag--danger',
};

@Component({
  selector: 'app-diagnostic-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, SlicePipe],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Diagnóstico</h1>
        <p class="wtn-page-desc">Cláusula 4 · coletado pelo Motor de Workflow de Preenchimento.</p>
      </div>
    </header>

    <div class="wtn-note">
      O Diagnóstico é coletado via <strong>template de diagnóstico</strong> atribuído a um preenchedor
      (membro ou externo via link). O preenchimento <strong>assinado</strong> torna-se a fonte do
      diagnóstico vigente desta organização — alimentando as sugestões da Visão Consolidada.
    </div>

    <!-- Templates de diagnóstico -->
    <section class="wtn-card block">
      <div class="block-head">
        <span class="block-title">Templates de diagnóstico</span>
        <a routerLink="/app/form-templates" class="block-link">Gerenciar templates →</a>
      </div>

      @if (loadingTemplates()) {
        <div class="row-muted">Carregando templates…</div>
      } @else if (diagTemplates().length === 0) {
        <div class="row-empty">
          <span>Nenhum template de diagnóstico ainda.</span>
          <a routerLink="/app/form-templates" class="wtn-btn-primary">Criar template</a>
        </div>
      } @else {
        @for (t of diagTemplates(); track t.id) {
          <div class="list-row">
            <span class="row-title">{{ t.title }}</span>
            <span class="wtn-tag {{ templateClass(t.status) }}">{{ templateLabel(t.status) }}</span>
            <span class="row-meta">{{ t.schema.length }} campo(s)</span>
            <a [routerLink]="['/app', 'form-assignments']" [queryParams]="{ template_id: t.id }" class="row-action">
              Atribuir →
            </a>
          </div>
        }
      }
    </section>

    <!-- Diagnósticos atribuídos -->
    <section class="wtn-card block">
      <div class="block-head">
        <span class="block-title">Diagnósticos atribuídos</span>
        <a routerLink="/app/form-assignments" class="block-link">Ver todos →</a>
      </div>
      @if (loadingAssignments()) {
        <div class="row-muted">Carregando…</div>
      } @else if (diagAssignments().length === 0) {
        <div class="row-muted">Nenhuma atribuição de diagnóstico ainda.</div>
      } @else {
        @for (a of diagAssignments(); track a.id) {
          <div class="list-row">
            <span class="row-title">{{ a.respondent_email ?? a.respondent_user_id ?? 'membro' }}</span>
            <span class="wtn-tag {{ assignmentClass(a.status) }}">{{ assignmentStatusLabel(a.status) }}</span>
            @if (a.deadline_at) {
              <span class="row-meta">prazo {{ a.deadline_at | slice: 0 : 10 }}</span>
            }
          </div>
        }
      }
    </section>

    <!-- Diagnóstico vigente -->
    <section class="wtn-card block">
      <div class="block-head">
        <span class="block-title">Diagnóstico vigente</span>
        <span class="wtn-tag {{ status() === 'completed' ? 'wtn-tag--success' : 'wtn-tag--neutral' }}">
          {{ statusLabel() }}
        </span>
      </div>

      @if (loadingDiagnostic()) {
        <div class="row-muted">Carregando…</div>
      } @else if (intake()) {
        <p class="meta">
          Fonte: <strong>{{ intake()!.source }}</strong>
          @if (intake()!.completedAt) { · concluído em {{ intake()!.completedAt | slice: 0 : 10 }} }
        </p>
        @if (intake()!.answers.length) {
          <div class="answers">
            @for (a of intake()!.answers; track a.key) {
              <div class="answer-row">
                <span class="a-key">{{ a.key }}</span>
                <span class="a-val">{{ a.value }}</span>
              </div>
            }
          </div>
        } @else {
          <div class="row-muted">Sem respostas registradas.</div>
        }
        @if (intake()!.assignmentId) {
          <a [routerLink]="['/app', 'form-assignments']" class="row-action">Ver atribuição na linha do tempo →</a>
        }
      } @else {
        <div class="row-muted">
          Nenhum diagnóstico preenchido ainda. Atribua um template acima para começar.
        </div>
      }
    </section>
  `,
  styles: `
    :host { display: block; }

    .wtn-note {
      background: var(--wtn-info-soft);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-info);
      font-size: 12.5px;
      line-height: 1.55;
      margin-bottom: 16px;
      padding: 13px 16px;
    }

    .block {
      background: var(--wtn-card);
      border: 1px solid var(--wtn-border);
      border-radius: var(--wtn-r-lg);
      box-shadow: var(--wtn-e1);
      margin-bottom: 16px;
      padding: 18px 20px;
    }

    .block-head {
      align-items: center;
      display: flex;
      gap: 10px;
      justify-content: space-between;
      margin-bottom: 12px;
    }

    .block-title {
      color: var(--wtn-text);
      font-size: 13px;
      font-weight: 600;
    }

    .block-link,
    .row-action {
      color: var(--wtn-primary);
      font-size: 12px;
      font-weight: 600;
      text-decoration: none;
      white-space: nowrap;
    }

    .block-link:hover,
    .row-action:hover { text-decoration: underline; }

    .list-row {
      align-items: center;
      border-bottom: 1px solid var(--wtn-surface-2);
      display: flex;
      gap: 12px;
      padding: 11px 0;
    }

    .list-row:last-child { border-bottom: 0; }

    .row-title {
      color: var(--wtn-text);
      flex: 1;
      font-size: 13px;
      font-weight: 500;
      min-width: 0;
    }

    .row-meta {
      color: var(--wtn-muted);
      font-size: 11.5px;
    }

    .row-muted {
      color: var(--wtn-text-2);
      font-size: 13px;
      padding: 4px 0;
    }

    .row-empty {
      align-items: center;
      color: var(--wtn-text-2);
      display: flex;
      font-size: 13px;
      gap: 14px;
      justify-content: space-between;
    }

    .wtn-btn-primary {
      background: var(--wtn-primary);
      border-radius: var(--wtn-r-md);
      color: var(--wtn-primary-contrast);
      font-size: 12.5px;
      font-weight: 600;
      padding: 8px 16px;
      text-decoration: none;
      white-space: nowrap;
    }

    .wtn-btn-primary:hover { background: var(--wtn-primary-hover); }

    .meta {
      color: var(--wtn-text-2);
      font-size: 12.5px;
      margin: 0 0 12px;
    }

    .meta strong { color: var(--wtn-text); }

    .answers {
      display: flex;
      flex-direction: column;
      gap: 2px;
      margin-bottom: 12px;
    }

    .answer-row {
      border-bottom: 1px solid var(--wtn-surface-2);
      display: grid;
      font-size: 13px;
      gap: 16px;
      grid-template-columns: 1fr 2fr;
      padding: 8px 0;
    }

    .a-key { color: var(--wtn-text-2); font-weight: 600; }
    .a-val { color: var(--wtn-text); }
  `,
})
export class DiagnosticPage implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly templates = signal<FormTemplate[]>([]);
  protected readonly assignments = signal<FormAssignment[]>([]);
  protected readonly loadingTemplates = signal(true);
  protected readonly loadingAssignments = signal(true);
  protected readonly loadingDiagnostic = signal(true);
  protected readonly status = signal<Diagnostic['status']>('draft');
  protected readonly intake = signal<IntakeView | null>(null);

  protected readonly diagTemplates = computed(() =>
    this.templates().filter((t) => t.kind === 'diagnostic' && t.status !== 'archived'),
  );

  protected readonly diagAssignments = computed(() =>
    this.assignments().filter((a) => a.kind === 'diagnostic'),
  );

  protected statusLabel(): string {
    return this.status() === 'completed' ? 'Concluído' : 'Rascunho';
  }

  protected assignmentStatusLabel(s: AssignmentStatus): string {
    return ASSIGNMENT_STATUS_LABELS[s];
  }

  protected assignmentClass(s: AssignmentStatus): string {
    return ASSIGNMENT_STATUS_CLASS[s];
  }

  protected templateLabel(s: FormTemplate['status']): string {
    return s === 'active' ? 'Ativo' : s === 'draft' ? 'Rascunho' : 'Arquivado';
  }

  protected templateClass(s: FormTemplate['status']): string {
    return s === 'active' ? 'wtn-tag--success' : s === 'draft' ? 'wtn-tag--neutral' : 'wtn-tag--danger';
  }

  ngOnInit(): void {
    this.api.listTemplates().subscribe({
      next: (list) => {
        this.templates.set(list);
        this.loadingTemplates.set(false);
      },
      error: () => this.loadingTemplates.set(false),
    });

    this.api.listAssignments().subscribe({
      next: (list) => {
        this.assignments.set(list);
        this.loadingAssignments.set(false);
      },
      error: () => this.loadingAssignments.set(false),
    });

    this.api.getDiagnostic().subscribe({
      next: (d) => {
        this.status.set(d.status);
        this.parseSections(d.sections);
        this.loadingDiagnostic.set(false);
      },
      error: () => this.loadingDiagnostic.set(false),
    });
  }

  /** Só consideramos o diagnóstico vigente quando vem do workflow (form_intake). */
  private parseSections(sections: Record<string, unknown>): void {
    const fi = sections['form_intake'] as Record<string, unknown> | undefined;
    if (fi && typeof fi === 'object') {
      const answers = (fi['answers'] as Record<string, unknown>) ?? {};
      this.intake.set({
        source: typeof fi['source'] === 'string' ? (fi['source'] as string) : 'workflow',
        assignmentId: typeof fi['assignment_id'] === 'string' ? (fi['assignment_id'] as string) : null,
        completedAt: typeof fi['completed_at'] === 'string' ? (fi['completed_at'] as string) : null,
        answers: this.toRows(answers),
      });
    }
  }

  private toRows(obj: Record<string, unknown>): { key: string; value: string }[] {
    return Object.entries(obj).map(([key, value]) => ({ key, value: this.fmt(value) }));
  }

  private fmt(v: unknown): string {
    if (v === true) return 'Sim';
    if (v === false) return 'Não';
    if (v === null || v === undefined || v === '') return '—';
    return String(v);
  }
}
