import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';

interface ItemGuidance {
  seed_item_id: string;
  ref_code: string;
  referencia: string;
  objetivo: string;
  como_avaliar: string[];
  evidencias_esperadas: string[];
  nota: string | null;
}

interface LegendEntry {
  id: string;
  code: string;
  label: string;
  definition: string;
  order: number;
}

interface GuidanceResponse {
  items: ItemGuidance[];
  legend: { status: LegendEntry[]; priority: LegendEntry[] };
}

@Component({
  selector: 'app-gap-guidance-admin',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <header class="wtn-page-header">
      <div>
        <h1 class="wtn-page-title">Orientação do Gap — Administração</h1>
        <p class="wtn-page-desc">
          Conteúdo canônico da plataforma · editado pelo Super Admin · reflete em todas as organizações.
        </p>
      </div>
    </header>

    @if (loading()) {
      <div class="wtn-loading-row"><div class="wtn-spinner"></div><span>Carregando…</span></div>
    } @else if (items().length === 0) {
      <div class="wtn-empty">Nenhum item de orientação. Verifique se o catálogo (seed) foi carregado.</div>
    } @else {
      <section class="admin-shell">
        <aside class="item-list">
          @for (it of items(); track it.seed_item_id) {
            <button type="button" class="item-row" [class.item-row--active]="selectedRef() === it.ref_code"
                    (click)="select(it)">
              <span class="item-ref">{{ it.ref_code }}</span>
            </button>
          }
        </aside>

        <div class="editor">
          @if (selected(); as g) {
            <div class="editor-head">
              <div class="editor-ref">{{ g.referencia }}</div>
            </div>
            <div class="field">
              <label>Objetivo</label>
              <textarea rows="3" [(ngModel)]="form.objetivo"></textarea>
            </div>
            <div class="field">
              <label>Como avaliar (uma pergunta por linha)</label>
              <textarea rows="5" [(ngModel)]="form.como_avaliar"></textarea>
            </div>
            <div class="field">
              <label>Evidências esperadas (uma por linha)</label>
              <textarea rows="5" [(ngModel)]="form.evidencias_esperadas"></textarea>
            </div>
            <div class="field">
              <label>Nota (opcional)</label>
              <input type="text" [(ngModel)]="form.nota" />
            </div>
            <div class="actions">
              <button type="button" class="btn" (click)="saveItem()" [disabled]="saving()">
                {{ saving() ? 'Salvando…' : 'Salvar orientação' }}
              </button>
            </div>
          } @else {
            <div class="editor-empty">Selecione um item à esquerda para editar a orientação.</div>
          }

          <div class="legend-editor">
            <div class="legend-title">Legenda — Status e Prioridade</div>
            @for (e of legend(); track e.id) {
              <div class="legend-row">
                <span class="legend-label">{{ e.label }}</span>
                <input type="text" [(ngModel)]="legendDraft[e.id]" [placeholder]="e.definition" />
                <button type="button" class="btn btn--sm" (click)="saveLegend(e)">Salvar</button>
              </div>
            }
          </div>
        </div>
      </section>
    }
  `,
  styles: `
    :host { display: block; }
    .wtn-loading-row { align-items: center; color: var(--wtn-text-2); display: flex; gap: 12px; padding: 28px 0; }
    .admin-shell {
      background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg);
      display: grid; grid-template-columns: 160px 1fr; min-height: 520px; overflow: hidden;
    }
    .item-list { border-right: 1px solid var(--wtn-border); overflow: auto; max-height: 70vh; }
    .item-row {
      background: none; border: 0; border-bottom: 1px solid var(--wtn-surface-2); cursor: pointer;
      display: block; padding: 9px 14px; text-align: left; width: 100%;
    }
    .item-row:hover { background: var(--wtn-surface-2); }
    .item-row--active { background: var(--wtn-primary-soft); }
    .item-ref { color: var(--wtn-text); font-family: var(--wtn-font-mono); font-size: 12px; }
    .editor { display: flex; flex-direction: column; gap: 14px; padding: 20px; }
    .editor-ref { color: var(--wtn-primary); font-family: var(--wtn-font-mono); font-size: 12.5px; font-weight: 600; }
    .field { display: flex; flex-direction: column; gap: 6px; }
    .field label { color: var(--wtn-text-2); font-size: 12px; font-weight: 500; }
    .field input, .field textarea {
      background: var(--wtn-surface); border: 1px solid var(--wtn-border-strong); border-radius: var(--wtn-r-md);
      color: var(--wtn-text); font: inherit; font-size: 13px; padding: 8px 11px; width: 100%; resize: vertical;
    }
    .field input:focus, .field textarea:focus {
      border-color: var(--wtn-focus); box-shadow: 0 0 0 3px color-mix(in srgb, var(--wtn-focus) 26%, transparent); outline: 0;
    }
    .btn {
      background: var(--wtn-primary); border: 0; border-radius: var(--wtn-r-md); color: var(--wtn-primary-contrast);
      cursor: pointer; font: inherit; font-size: 13px; font-weight: 600; padding: 9px 18px;
    }
    .btn:hover:not(:disabled) { background: var(--wtn-primary-hover); }
    .btn:disabled { opacity: .6; cursor: not-allowed; }
    .btn--sm { padding: 6px 12px; font-size: 12px; }
    .editor-empty { color: var(--wtn-text-2); font-style: italic; }
    .legend-editor { border-top: 1px solid var(--wtn-surface-2); margin-top: 8px; padding-top: 16px; }
    .legend-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; margin-bottom: 12px; text-transform: uppercase; }
    .legend-row { align-items: center; display: grid; gap: 10px; grid-template-columns: 150px 1fr auto; margin-bottom: 8px; }
    .legend-label { color: var(--wtn-text); font-size: 12.5px; font-weight: 600; }
    .legend-row input { background: var(--wtn-surface); border: 1px solid var(--wtn-border-strong); border-radius: var(--wtn-r-md); color: var(--wtn-text); font: inherit; font-size: 12.5px; padding: 7px 10px; }
  `,
})
export class GapGuidanceAdminPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly messages = inject(MessageService);

  protected readonly loading = signal(true);
  protected readonly items = signal<ItemGuidance[]>([]);
  protected readonly legend = signal<LegendEntry[]>([]);
  protected readonly selectedRef = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected legendDraft: Record<string, string> = {};

  protected form = { objetivo: '', como_avaliar: '', evidencias_esperadas: '', nota: '' };

  protected readonly selected = computed<ItemGuidance | null>(
    () => this.items().find((i) => i.ref_code === this.selectedRef()) ?? null,
  );

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.api.get<GuidanceResponse>('/gap/guidance').subscribe({
      next: (g) => {
        this.items.set(g.items);
        this.legend.set([...g.legend.status, ...g.legend.priority]);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  protected select(it: ItemGuidance): void {
    this.selectedRef.set(it.ref_code);
    this.form = {
      objetivo: it.objetivo,
      como_avaliar: it.como_avaliar.join('\n'),
      evidencias_esperadas: it.evidencias_esperadas.join('\n'),
      nota: it.nota ?? '',
    };
  }

  private toList(text: string): string[] {
    return text.split('\n').map((l) => l.trim()).filter(Boolean);
  }

  protected saveItem(): void {
    const g = this.selected();
    if (!g) return;
    this.saving.set(true);
    const body = {
      objetivo: this.form.objetivo,
      como_avaliar: this.toList(this.form.como_avaliar),
      evidencias_esperadas: this.toList(this.form.evidencias_esperadas),
      nota: this.form.nota || null,
    };
    this.api.put<ItemGuidance>(`/gap/guidance/items/${g.seed_item_id}`, body).subscribe({
      next: (updated) => {
        this.items.update((list) => list.map((i) => (i.seed_item_id === updated.seed_item_id ? updated : i)));
        this.messages.add({ severity: 'success', summary: 'Orientação salva', detail: g.ref_code, life: 2500 });
        this.saving.set(false);
      },
      error: (e) => {
        this.messages.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  protected saveLegend(entry: LegendEntry): void {
    const definition = this.legendDraft[entry.id];
    if (!definition?.trim()) return;
    this.api.put<LegendEntry>(`/gap/guidance/legend/${entry.id}`, { definition }).subscribe({
      next: (updated) => {
        this.legend.update((list) => list.map((e) => (e.id === updated.id ? updated : e)));
        this.legendDraft[entry.id] = '';
        this.messages.add({ severity: 'success', summary: 'Legenda atualizada', life: 2500 });
      },
      error: (e) => this.messages.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message }),
    });
  }
}
