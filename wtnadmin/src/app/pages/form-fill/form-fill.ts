import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { InputMaskModule } from 'primeng/inputmask';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AssignmentStatus, FormAssignment, FormField } from '@app/core/models';

const STATUS_LABELS: Record<AssignmentStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em preenchimento',
  submitted: 'Preenchido',
  signed: 'Assinado',
  completed: 'Concluído',
  cancelled: 'Cancelado',
};

/** Ordena por `order` e agrupa por `section` (campos sem seção ficam num grupo sem título). */
export function groupFields(fields: FormField[]): { section: string; items: FormField[] }[] {
  const sorted = [...fields].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  const groups: { section: string; items: FormField[] }[] = [];
  for (const f of sorted) {
    const sec = (f.section ?? '').trim();
    let g = groups.find((x) => x.section === sec);
    if (!g) {
      g = { section: sec, items: [] };
      groups.push(g);
    }
    g.items.push(f);
  }
  return groups;
}

@Component({
  selector: 'app-form-fill',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CardModule, ButtonModule, TagModule, InputMaskModule],
  template: `
    @if (loading()) {
      <p class="hint">Carregando formulário...</p>
    } @else if (!assignment()) {
      <p class="hint error">Formulário não encontrado.</p>
    } @else {
      <div class="fill-header">
        <h2>{{ assignment()!.title }}</h2>
        <p-tag [value]="statusLabel(assignment()!.status)" />
        @if (assignment()!.overdue) { <span class="overdue">ATRASADO</span> }
      </div>

      @if (assignment()!.instructions) {
        <p class="instructions">{{ assignment()!.instructions }}</p>
      }

      @if (assignment()!.status === 'pending') {
        <p-card>
          <p>Este formulário foi atribuído a você. Clique em "Assumir" para começar a preencher.</p>
          <p-button label="Assumir formulário" (onClick)="claim()" [disabled]="saving()" />
        </p-card>
      }

      @if (['in_progress', 'submitted'].includes(assignment()!.status)) {
        <p-card>
          @for (group of groups(); track group.section) {
            @if (group.section) { <h3 class="section-h">{{ group.section }}</h3> }
            @for (field of group.items; track field.key) {
              <div class="field-row">
                <label>
                  {{ field.label }}
                  @if (field.required) { <span class="req">*</span> }
                </label>
                @switch (field.type) {
                  @case ('boolean') {
                    <div class="radio-row">
                      <label class="opt"><input type="radio" [name]="field.key" [value]="true" [(ngModel)]="answers()[field.key]" /> Sim</label>
                      <label class="opt"><input type="radio" [name]="field.key" [value]="false" [(ngModel)]="answers()[field.key]" /> Não</label>
                    </div>
                  }
                  @case ('number') {
                    <input type="number" [(ngModel)]="answers()[field.key]" />
                  }
                  @case ('textarea') {
                    <textarea rows="3" [(ngModel)]="answers()[field.key]"></textarea>
                  }
                  @case ('select') {
                    <select [(ngModel)]="answers()[field.key]">
                      <option value="">— Selecione —</option>
                      @for (opt of (field.options ?? []); track opt) {
                        <option [value]="opt">{{ opt }}</option>
                      }
                    </select>
                  }
                  @case ('text') {
                    @if (field.mask) {
                      <p-inputmask [mask]="field.mask" [(ngModel)]="answers()[field.key]" />
                    } @else {
                      <input type="text" [(ngModel)]="answers()[field.key]" />
                    }
                  }
                  @default {
                    <input type="text" [(ngModel)]="answers()[field.key]" />
                  }
                }
                @if (field.help_text) { <small class="help">{{ field.help_text }}</small> }
              </div>
            }
          }

          <div class="actions footer">
            <p-button label="Salvar rascunho" severity="secondary" (onClick)="saveAnswers()" [disabled]="saving()" />
            @if (assignment()!.status !== 'submitted') {
              <p-button label="Enviar" (onClick)="submit()" [disabled]="saving()" />
            }
            <p-button label="← Voltar" severity="secondary" (onClick)="goBack()" />
          </div>
        </p-card>
      }

      @if (['signed', 'completed', 'cancelled'].includes(assignment()!.status)) {
        <p-card>
          <p class="hint">
            @if (assignment()!.status === 'signed') { Este formulário foi assinado e aguarda conclusão. }
            @else if (assignment()!.status === 'completed') { Este formulário foi concluído com sucesso. }
            @else { Esta atribuição foi cancelada. }
          </p>
          <p-button label="← Voltar para atribuições" severity="secondary" (onClick)="goBack()" />
        </p-card>
      }
    }
  `,
  styles: `
    .fill-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap; }
    h2 { margin: 0; flex: 1; }
    .section-h { margin: 1rem 0 0.5rem; font-size: 1rem; border-bottom: 1px solid var(--p-content-border-color, #3a3a3a); padding-bottom: 0.3rem; }
    .overdue { background: #c0392b; color: #fff; border-radius: 4px; padding: 0.15rem 0.5rem; font-size: 0.75rem; font-weight: 700; }
    .instructions { opacity: 0.8; font-size: 0.9rem; font-style: italic; border-left: 3px solid var(--p-content-border-color, #444); padding-left: 0.75rem; margin-bottom: 1rem; }
    .field-row { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.9rem; }
    .field-row label { font-size: 0.88rem; font-weight: 600; opacity: 0.85; }
    .req { color: #e74c3c; margin-left: 0.2rem; }
    .radio-row { display: flex; gap: 1.25rem; }
    .radio-row .opt { display: flex; align-items: center; gap: 0.4rem; font-weight: 400; }
    .help { opacity: 0.6; font-size: 0.8rem; font-weight: 400; }
    input[type='text'], input[type='number'], textarea, select {
      width: 100%; background: var(--p-content-background, #1e1e1e);
      border: 1px solid var(--p-content-border-color, #444); border-radius: 6px;
      padding: 0.4rem 0.55rem; font: inherit; color: inherit;
    }
    input[type='radio'] { width: 1.05rem; height: 1.05rem; }
    .actions { display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap; }
    .actions.footer { border-top: 1px solid var(--p-content-border-color, #333); padding-top: 0.75rem; margin-top: 1rem; }
    .hint { opacity: 0.75; font-style: italic; }
    .hint.error { color: #e74c3c; }
  `,
})
export class FormFillPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly assignment = signal<FormAssignment | null>(null);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly fields = signal<FormField[]>([]);
  protected readonly answers = signal<Record<string, unknown>>({});
  protected readonly groups = computed(() => groupFields(this.fields()));

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) { this.loading.set(false); return; }
    this.api.getAssignment(id).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.fields.set(a.fields_snapshot);
        this.answers.set({ ...a.answers });
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  protected statusLabel(s: AssignmentStatus): string { return STATUS_LABELS[s]; }

  protected claim(): void {
    const id = this.assignment()!.id;
    this.saving.set(true);
    this.api.claimAssignment(id).subscribe({
      next: (a) => { this.assignment.set(a); this.saving.set(false); },
      error: () => this.saving.set(false),
    });
  }

  protected saveAnswers(): void {
    const id = this.assignment()!.id;
    this.saving.set(true);
    this.api.saveAnswers(id, this.answers()).subscribe({
      next: (a) => {
        this.assignment.set(a);
        this.saving.set(false);
        this.messages.add({ severity: 'success', summary: 'Rascunho salvo', life: 2500 });
      },
      error: () => this.saving.set(false),
    });
  }

  protected submit(): void {
    const id = this.assignment()!.id;
    this.saving.set(true);
    this.api.saveAnswers(id, this.answers()).subscribe({
      next: () => {
        this.api.submitAssignment(id).subscribe({
          next: (a) => {
            this.assignment.set(a);
            this.saving.set(false);
            this.messages.add({ severity: 'success', summary: 'Formulário enviado!', life: 4000 });
          },
          error: (err) => {
            this.saving.set(false);
            const detail = err?.error?.detail ?? 'Verifique os campos obrigatórios.';
            this.messages.add({ severity: 'error', summary: 'Erro ao enviar', detail, life: 5000 });
          },
        });
      },
      error: () => this.saving.set(false),
    });
  }

  protected goBack(): void {
    void this.router.navigate(['/app', 'form-assignments']);
  }
}
