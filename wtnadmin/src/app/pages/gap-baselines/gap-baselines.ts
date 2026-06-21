import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe, PercentPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { GapAssessment, GapBaseline, GapBaselineComparison } from '@app/core/models';

const CLASSIFICATION_OPTIONS = [
  { label: 'Público', value: 'publico' },
  { label: 'Uso interno', value: 'uso_interno' },
  { label: 'Confidencial', value: 'confidencial' },
  { label: 'Restrito', value: 'restrito' },
];

@Component({
  selector: 'app-gap-baselines',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    DatePipe,
    FormsModule,
    PercentPipe,
    ButtonModule,
    CardModule,
    DialogModule,
    InputTextModule,
    SelectModule,
    TagModule,
  ],
  template: `
    <div class="page-header">
      <h2>Baselines — Gap Analysis</h2>
      <div class="flex gap-2">
        @if (canApprove()) {
          @if (assessment()?.draft_status === 'draft') {
            <p-button
              label="Enviar para revisão"
              icon="pi pi-send"
              severity="secondary"
              (onClick)="submitReview()"
              [loading]="submitting()"
            />
          }
          @if (assessment()?.draft_status === 'in_review') {
            <p-button
              label="Aprovar baseline"
              icon="pi pi-check"
              (onClick)="showApproveDialog()"
            />
          }
        }
      </div>
    </div>

    @if (assessment()?.draft_status === 'in_review') {
      <div class="alert-info mb-3">
        <i class="pi pi-info-circle mr-2"></i>
        Avaliação em revisão — pronta para aprovação de baseline.
      </div>
    }

    <!-- Lista de baselines -->
    @if (baselines().length === 0) {
      <p-card>
        <p class="text-center text-color-secondary p-4">Nenhuma baseline aprovada ainda.</p>
      </p-card>
    } @else {
      @for (b of baselines(); track b.id) {
        <p-card styleClass="mb-3">
          <div class="flex justify-between items-center">
            <div>
              <span class="font-bold text-lg">v{{ b.version_number }}</span>
              <span class="text-color-secondary ml-2 text-sm">
                Aprovada em {{ b.emitted_at | date:'dd/MM/yyyy HH:mm' }}
              </span>
            </div>
            <div class="flex gap-2 items-center">
              @if (b.overall_adherence !== null) {
                <span class="font-bold text-xl">{{ b.overall_adherence | percent:'1.0-1' }}</span>
              } @else {
                <span class="text-color-secondary">—</span>
              }
              <p-tag [value]="b.classification" severity="secondary" />
            </div>
          </div>
          @if (baselines().length > 1 && b.version_number < baselines()[0].version_number) {
            <div class="mt-2">
              <p-button
                label="Comparar com atual"
                icon="pi pi-chart-line"
                size="small"
                severity="secondary"
                (onClick)="compareWith(b)"
              />
            </div>
          }
        </p-card>
      }
    }

    <!-- Comparação -->
    @if (comparison()) {
      <p-card header="Comparação de Baselines" styleClass="mt-3">
        <div class="flex gap-4 justify-center text-center">
          <div>
            <div class="text-sm text-color-secondary">v{{ comparison()!.from_baseline.version_number }}</div>
            <div class="text-3xl font-bold">
              @if (comparison()!.from_baseline.overall_adherence !== null) {
                {{ comparison()!.from_baseline.overall_adherence! | percent:'1.0-1' }}
              } @else { — }
            </div>
          </div>
          <div class="self-center text-2xl">→</div>
          <div>
            <div class="text-sm text-color-secondary">v{{ comparison()!.to_baseline.version_number }}</div>
            <div class="text-3xl font-bold">
              @if (comparison()!.to_baseline.overall_adherence !== null) {
                {{ comparison()!.to_baseline.overall_adherence! | percent:'1.0-1' }}
              } @else { — }
            </div>
          </div>
          <div class="self-center">
            @if (comparison()!.overall_delta !== null) {
              <span
                class="text-2xl font-bold"
                [class.text-green-500]="comparison()!.overall_delta! > 0"
                [class.text-red-500]="comparison()!.overall_delta! < 0"
              >
                {{ comparison()!.overall_delta! > 0 ? '+' : '' }}{{ comparison()!.overall_delta! | percent:'1.0-1' }}
              </span>
            }
          </div>
        </div>
      </p-card>
    }

    <!-- Dialog aprovar -->
    <p-dialog
      header="Aprovar Baseline"
      [(visible)]="approveDialogVisible"
      [style]="{ width: '480px' }"
      [modal]="true"
    >
      <div class="flex flex-col gap-3">
        <div>
          <label class="block font-semibold mb-1">Classificação</label>
          <p-select
            [options]="classificationOptions"
            [(ngModel)]="approveClassification"
            optionLabel="label"
            optionValue="value"
            styleClass="w-full"
          />
        </div>
        <div>
          <label class="block font-semibold mb-1">Natureza da revisão</label>
          <input pInputText [(ngModel)]="approveNature" placeholder="Ex.: Emissão inicial" class="w-full" />
        </div>
      </div>
      <ng-template pTemplate="footer">
        <p-button label="Cancelar" severity="secondary" (onClick)="approveDialogVisible = false" />
        <p-button label="Aprovar" icon="pi pi-check" (onClick)="approveBaseline()" [loading]="approving()" />
      </ng-template>
    </p-dialog>
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .alert-info { background: var(--blue-100, #dbeafe); color: var(--blue-800, #1e40af); border-radius: 6px; padding: .75rem 1rem; }
  `],
})
export class GapBaselinesPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);

  assessment = signal<GapAssessment | null>(null);
  baselines = signal<GapBaseline[]>([]);
  comparison = signal<GapBaselineComparison | null>(null);
  loading = signal(true);
  submitting = signal(false);
  approving = signal(false);
  approveDialogVisible = false;
  approveClassification = 'uso_interno';
  approveNature = '';
  classificationOptions = CLASSIFICATION_OPTIONS;

  canApprove = computed(() => hasPermission(this.auth.currentRole(), 'approve_gap_baseline'));

  ngOnInit() {
    this.loadAssessment();
    this.loadBaselines();
  }

  private loadAssessment() {
    this.api.get<GapAssessment>('/gap/assessment').subscribe({
      next: (a) => this.assessment.set(a),
      error: () => {},
    });
  }

  private loadBaselines() {
    this.api.get<GapBaseline[]>('/gap/assessment/baselines').subscribe({
      next: (b) => { this.baselines.set(b); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  submitReview() {
    this.submitting.set(true);
    this.api.post<GapAssessment>('/gap/assessment/submit-review', {}).subscribe({
      next: (a) => {
        this.assessment.set(a);
        this.msg.add({ severity: 'success', summary: 'Enviado para revisão' });
        this.submitting.set(false);
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.submitting.set(false);
      },
    });
  }

  showApproveDialog() {
    this.approveClassification = 'uso_interno';
    this.approveNature = this.baselines().length === 0 ? 'Emissão inicial' : 'Revisão periódica';
    this.approveDialogVisible = true;
  }

  approveBaseline() {
    this.approving.set(true);
    this.api.post<GapBaseline>('/gap/assessment/approve', {
      classification: this.approveClassification,
      change_nature: this.approveNature,
    }).subscribe({
      next: (b) => {
        this.msg.add({ severity: 'success', summary: 'Baseline aprovada', detail: `v${b.version_number} registrada.` });
        this.approving.set(false);
        this.approveDialogVisible = false;
        this.loadAssessment();
        this.loadBaselines();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.approving.set(false);
      },
    });
  }

  compareWith(older: GapBaseline) {
    const latest = this.baselines()[0];
    this.api.get<GapBaselineComparison>(
      `/gap/assessment/baselines/compare?from_id=${older.id}&to_id=${latest.id}`
    ).subscribe({
      next: (c) => this.comparison.set(c),
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.message }),
    });
  }
}
