import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

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

@Component({
  selector: 'app-diagnostic-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardModule, ButtonModule, TagModule, RouterLink, SlicePipe],
  template: `
    <h2>Diagnóstico</h2>

    <p-card class="intro">
      <p class="hint">
        O Diagnóstico (Cláusula 4) é coletado pelo <strong>Motor de Workflow de Preenchimento</strong>:
        monte um template do tipo <em>diagnóstico</em>, atribua-o a um preenchedor (membro ou externo
        via link), e o preenchimento <strong>assinado</strong> torna-se a fonte do diagnóstico vigente
        desta organização — alimentando as sugestões heurísticas da Visão Consolidada.
      </p>
    </p-card>

    <!-- Templates de diagnóstico disponíveis -->
    <p-card class="block">
      <div class="block-header">
        <h3>Templates de diagnóstico</h3>
        <a routerLink="/app/form-templates" class="manage-link">Gerenciar templates →</a>
      </div>

      @if (loadingTemplates()) {
        <p class="hint">Carregando templates...</p>
      } @else if (diagTemplates().length === 0) {
        <p class="empty">
          Nenhum template de diagnóstico ainda.
        </p>
        <p-button label="Criar template de diagnóstico" icon="pi pi-plus" routerLink="/app/form-templates" />
      } @else {
        @for (t of diagTemplates(); track t.id) {
          <div class="tpl-row">
            <span class="tpl-title">{{ t.title }}</span>
            <p-tag [value]="t.status === 'active' ? 'Ativo' : t.status === 'draft' ? 'Rascunho' : 'Arquivado'"
              [severity]="t.status === 'active' ? 'success' : t.status === 'draft' ? 'secondary' : 'danger'" />
            <span class="tpl-fields">{{ t.schema.length }} campo(s)</span>
            <a [routerLink]="['/app', 'form-assignments']" [queryParams]="{ template_id: t.id }"
              class="assign-link">Atribuir →</a>
          </div>
        }
      }
    </p-card>

    <!-- Atribuições de diagnóstico -->
    <p-card class="block">
      <div class="block-header">
        <h3>Diagnósticos atribuídos</h3>
        <a routerLink="/app/form-assignments" class="manage-link">Ver todos →</a>
      </div>
      @if (loadingAssignments()) {
        <p class="hint">Carregando...</p>
      } @else if (diagAssignments().length === 0) {
        <p class="empty">Nenhuma atribuição de diagnóstico ainda.</p>
      } @else {
        @for (a of diagAssignments(); track a.id) {
          <div class="asgn-row">
            <span class="asgn-respondent">{{ a.respondent_email ?? a.respondent_user_id ?? 'membro' }}</span>
            <span class="asgn-status">{{ assignmentStatusLabel(a.status) }}</span>
            @if (a.deadline_at) { <span class="asgn-date">prazo {{ a.deadline_at | slice:0:10 }}</span> }
          </div>
        }
      }
    </p-card>

    <!-- Diagnóstico vigente -->
    <p-card class="block">
      <div class="block-header">
        <h3>Diagnóstico vigente</h3>
        <p-tag [value]="statusLabel()" [severity]="status() === 'completed' ? 'success' : 'secondary'" />
      </div>

      @if (loadingDiagnostic()) {
        <p class="hint">Carregando...</p>
      } @else if (intake()) {
        <p class="meta">
          Fonte: <strong>{{ intake()!.source }}</strong>
          @if (intake()!.completedAt) { · concluído em {{ intake()!.completedAt | slice:0:10 }} }
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
          <p class="empty">Sem respostas registradas.</p>
        }
        @if (intake()!.assignmentId) {
          <a [routerLink]="['/app', 'form-assignments']" class="assign-link">Ver atribuição na linha do tempo →</a>
        }
      } @else {
        <p class="empty">
          Nenhum diagnóstico preenchido ainda. Atribua um template de diagnóstico acima para começar.
        </p>
      }
    </p-card>
  `,
  styles: `
    h2 { margin-top: 0; }
    h3 { margin: 0; }
    .hint { opacity: 0.8; font-size: 0.9rem; margin: 0; }
    .empty { opacity: 0.7; font-style: italic; margin: 0.25rem 0 0.75rem; }
    .intro { margin-bottom: 1rem; }
    .block { margin-bottom: 1rem; }
    .block-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }
    .block-header h3 { flex: 1; }
    .manage-link, .assign-link { font-size: 0.85rem; color: var(--p-primary-color, #6c63ff); text-decoration: none; }
    .manage-link:hover, .assign-link:hover { text-decoration: underline; }
    .tpl-row {
      display: flex; align-items: center; gap: 0.75rem; padding: 0.55rem 0;
      border-bottom: 1px solid var(--p-content-border-color, #333);
    }
    .tpl-row:last-child { border-bottom: none; }
    .tpl-title { font-weight: 500; flex: 1; }
    .tpl-fields { font-size: 0.82rem; opacity: 0.7; }
    .asgn-row { display: flex; gap: 1rem; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid var(--p-content-border-color, #2a2a2a); font-size: 0.88rem; }
    .asgn-row:last-child { border-bottom: none; }
    .asgn-respondent { flex: 1; }
    .asgn-status { opacity: 0.8; }
    .asgn-date { font-size: 0.8rem; opacity: 0.6; }
    .meta { font-size: 0.85rem; opacity: 0.8; margin: 0 0 0.75rem; }
    .meta.legacy { font-style: italic; }
    .answers { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
    .answer-row {
      display: grid; grid-template-columns: 1fr 2fr; gap: 1rem; padding: 0.3rem 0;
      border-bottom: 1px solid var(--p-content-border-color, #2a2a2a); font-size: 0.9rem;
    }
    .a-key { font-weight: 600; opacity: 0.8; }
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

  ngOnInit(): void {
    this.api.listTemplates().subscribe({
      next: (list) => { this.templates.set(list); this.loadingTemplates.set(false); },
      error: () => this.loadingTemplates.set(false),
    });

    this.api.listAssignments().subscribe({
      next: (list) => { this.assignments.set(list); this.loadingAssignments.set(false); },
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
