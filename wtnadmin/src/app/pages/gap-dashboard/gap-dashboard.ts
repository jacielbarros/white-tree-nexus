import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
} from '@angular/core';
import { PercentPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { GapAssessmentItem, GapDashboard, GapStatus } from '@app/core/models';

const STATUS_LABELS: Record<GapStatus, string> = {
  not_filled: 'Não avaliado',
  meets: 'Atende',
  partial: 'Parcialmente atende',
  not_meet: 'Não atende',
  not_applicable: 'N/A',
};

@Component({
  selector: 'app-gap-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PercentPipe, RouterLink, ButtonModule, CardModule, TagModule],
  template: `
    <div class="page-header">
      <h2>Dashboard de Aderência — Gap Analysis</h2>
      <a routerLink="../gap-analysis">
        <p-button label="Ver matriz" icon="pi pi-table" severity="secondary" />
      </a>
    </div>

    @if (loading()) {
      <div class="p-4 text-center">Carregando métricas…</div>
    } @else if (!dashboard()) {
      <p-card>
        <p class="text-center p-4">
          Sem dados. <a routerLink="../gap-analysis">Adote o catálogo e avalie os itens.</a>
        </p>
      </p-card>
    } @else {
      <!-- Aderência geral -->
      <div class="grid grid-cols-2 gap-3 mb-4">
        <p-card header="Aderência Geral">
          <div class="text-5xl font-bold text-center" [class.text-color-secondary]="dashboard()!.overall_adherence === null">
            @if (dashboard()!.overall_adherence !== null) {
              {{ dashboard()!.overall_adherence! | percent:'1.0-1' }}
            } @else {
              —
            }
          </div>
          <p class="text-center text-sm text-color-secondary mt-1">
            Completude: {{ dashboard()!.completeness | percent:'1.0-0' }}
          </p>
        </p-card>

        <p-card header="Distribuição por Status">
          @for (entry of statusEntries(); track entry[0]) {
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm">{{ statusLabel(entry[0]) }}</span>
              <span class="font-semibold">{{ entry[1] }}</span>
            </div>
          }
        </p-card>
      </div>

      <!-- Por dimensão -->
      <p-card header="Por Dimensão" styleClass="mb-3">
        @for (entry of dimensionEntries(); track entry[0]) {
          <div class="flex justify-between items-center mb-2">
            <span>{{ dimLabel(entry[0]) }}</span>
            <span class="font-semibold">
              @if (entry[1] !== null) {
                {{ entry[1] | percent:'1.0-1' }}
              } @else { — }
            </span>
          </div>
        }
      </p-card>

      <!-- Lista de lacunas -->
      <p-card header="Lacunas Identificadas (partial + não atende)">
        @if (gaps().length === 0) {
          <p class="text-color-secondary">Sem lacunas identificadas.</p>
        } @else {
          <div class="gap-list">
            @for (item of gaps(); track item.id) {
              <div class="gap-row">
                <div class="gap-row__meta">
                  <span class="gap-row__ref">{{ item.ref_code }}</span>
                  @if (item.priority) {
                    <p-tag [value]="item.priority" [severity]="prioritySeverity(item.priority)" />
                  }
                  <p-tag
                    [value]="item.status === 'partial' ? 'Parcial' : 'Não atende'"
                    [severity]="item.status === 'partial' ? 'warn' : 'danger'"
                  />
                </div>
                <div class="gap-row__name">{{ item.name }}</div>
                @if (item.findings) {
                  <div class="gap-row__findings text-sm text-color-secondary">{{ item.findings }}</div>
                }
              </div>
            }
          </div>
        }
      </p-card>
    }
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .gap-list { display: flex; flex-direction: column; gap: .75rem; }
    .gap-row { border: 1px solid var(--surface-border); border-radius: 6px; padding: .75rem; }
    .gap-row__meta { display: flex; gap: .5rem; align-items: center; margin-bottom: .25rem; }
    .gap-row__ref { font-weight: 700; font-size: .85rem; }
    .gap-row__findings { margin-top: .25rem; }
  `],
})
export class GapDashboardPage implements OnInit {
  private api = inject(ApiService);
  private msg = inject(MessageService);

  dashboard = signal<GapDashboard | null>(null);
  gaps = signal<GapAssessmentItem[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.api.get<GapDashboard>('/gap/assessment/dashboard').subscribe({
      next: (d) => {
        this.dashboard.set(d);
        this.loadGaps();
      },
      error: (e) => {
        if (e.status !== 404) this.msg.add({ severity: 'error', summary: 'Erro', detail: e.message });
        this.loading.set(false);
      },
    });
  }

  private loadGaps() {
    this.api.get<GapAssessmentItem[]>('/gap/assessment/gaps').subscribe({
      next: (g) => { this.gaps.set(g); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  statusEntries(): [string, number][] {
    return Object.entries(this.dashboard()?.status_distribution ?? {});
  }

  dimensionEntries(): [string, number | null][] {
    return Object.entries(this.dashboard()?.by_dimension ?? {});
  }

  statusLabel(s: string): string {
    return STATUS_LABELS[s as GapStatus] ?? s;
  }

  dimLabel(dim: string): string {
    return dim === 'clause' ? 'Cláusulas (4–10)' : 'Anexo A — Controles';
  }

  prioritySeverity(p: string): 'danger' | 'warn' | 'info' | 'secondary' {
    const map: Record<string, 'danger' | 'warn' | 'info' | 'secondary'> = {
      critical: 'danger', high: 'warn', medium: 'info', low: 'secondary',
    };
    return map[p] ?? 'secondary';
  }
}
