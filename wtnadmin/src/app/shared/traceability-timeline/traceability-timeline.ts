import { ChangeDetectionStrategy, Component, OnInit, inject, input, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';

import { ApiService } from '@app/core/api.service';
import { SgsiArtifactType, TimelineEntry } from '@app/core/models';

const KIND_LABELS: Record<TimelineEntry['kind'], string> = {
  evidence: 'Evidência',
  finding: 'Constatação',
  event: 'Evento',
};

/**
 * Timeline de rastreabilidade (read-only) de um artefato — Feature 014, US7.
 * Agrega evidências, constatações e eventos de custódia em ordem cronológica (só metadados).
 */
@Component({
  selector: 'app-traceability-timeline',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ButtonModule],
  template: `
    <section class="tl">
      <div class="tl__head">
        <div>
          <div class="tl__eyebrow">Rastreabilidade</div>
          <strong>{{ title() }}</strong>
        </div>
        <p-button icon="pi pi-refresh" label="Atualizar" severity="secondary" (onClick)="load()" [loading]="loading()" />
      </div>

      @if (loading()) {
        <div class="tl__empty">Carregando timeline…</div>
      } @else if (!entries().length) {
        <div class="tl__empty">Nenhum evento associado ainda.</div>
      } @else {
        <ol class="tl__list">
          @for (e of entries(); track e.ref_id + e.occurred_at) {
            <li class="tl__row tl__row--{{ e.kind }}">
              <span class="tl__dot"></span>
              <div class="tl__body">
                <div class="tl__line"><span class="tl__kind">{{ kindLabel(e.kind) }}</span><strong>{{ e.label }}</strong></div>
                <small>{{ e.detail }} · {{ formatDate(e.occurred_at) }}</small>
              </div>
            </li>
          }
        </ol>
      }
    </section>
  `,
  styles: `
    :host { display: block; }
    .tl { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); box-shadow: var(--wtn-e1); display: grid; gap: 10px; padding: 14px; }
    .tl__head { align-items: center; display: flex; gap: 12px; justify-content: space-between; }
    .tl__head strong { color: var(--wtn-text); font-size: 14px; }
    .tl__eyebrow { color: var(--wtn-muted); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .tl__empty { color: var(--wtn-text-2); font-size: 12.5px; }
    .tl__list { display: grid; gap: 4px; list-style: none; margin: 0; padding: 0; }
    .tl__row { display: grid; gap: 10px; grid-template-columns: 14px 1fr; padding: 4px 0; position: relative; }
    .tl__dot { background: var(--wtn-border-strong); border-radius: 50%; height: 9px; margin-top: 4px; width: 9px; }
    .tl__row--evidence .tl__dot { background: var(--wtn-primary); }
    .tl__row--finding .tl__dot { background: #e67e22; }
    .tl__body { display: grid; gap: 2px; }
    .tl__line { align-items: baseline; display: flex; gap: 8px; }
    .tl__line strong { color: var(--wtn-text); font-size: 12.5px; }
    .tl__kind { color: var(--wtn-muted); font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .tl__body small { color: var(--wtn-text-2); font-size: 11.5px; }
  `,
})
export class TraceabilityTimeline implements OnInit {
  private readonly api = inject(ApiService);

  readonly targetType = input.required<SgsiArtifactType>();
  readonly targetId = input.required<string>();
  readonly title = input('Linha do tempo');

  protected readonly loading = signal(false);
  protected readonly entries = signal<TimelineEntry[]>([]);

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.loading.set(true);
    this.api.listTimeline(this.targetType(), this.targetId()).subscribe({
      next: (rows) => {
        this.entries.set(rows);
        this.loading.set(false);
      },
      error: () => {
        this.entries.set([]);
        this.loading.set(false);
      },
    });
  }

  protected kindLabel(kind: TimelineEntry['kind']): string {
    return KIND_LABELS[kind];
  }

  protected formatDate(value: string): string {
    return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
  }
}
