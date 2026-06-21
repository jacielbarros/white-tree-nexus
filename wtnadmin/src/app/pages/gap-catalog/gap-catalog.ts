import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormControl, FormGroup, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { TooltipModule } from 'primeng/tooltip';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { GapCatalogItem, GapDimension } from '@app/core/models';

const DIMENSION_OPTIONS = [
  { label: 'Cláusula (4–10)', value: 'clause' },
  { label: 'Anexo A', value: 'annex_a' },
];

const THEME_OPTIONS = [
  { label: 'Organizacional', value: 'organizational' },
  { label: 'Pessoas', value: 'people' },
  { label: 'Físico', value: 'physical' },
  { label: 'Tecnológico', value: 'technological' },
];

const DIM_LABELS: Record<GapDimension, string> = {
  clause: 'Cláusulas (4–10)',
  annex_a: 'Anexo A — Controles',
};

@Component({
  selector: 'app-gap-catalog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    CardModule,
    DialogModule,
    InputTextModule,
    SelectModule,
    TagModule,
    TextareaModule,
    TooltipModule,
  ],
  template: `
    <div class="page-header">
      <h2>Catálogo de Itens — Gap Analysis</h2>
      <div class="flex gap-2">
        @if (canManage()) {
          <p-button
            label="Adotar catálogo 2022.1"
            icon="pi pi-download"
            severity="secondary"
            (onClick)="adoptSeed()"
            [loading]="adopting()"
            pTooltip="Adiciona itens do seed 2022.1 que ainda não existem (não apaga itens existentes)"
          />
          <p-button
            label="Novo item"
            icon="pi pi-plus"
            (onClick)="openNew()"
          />
        }
      </div>
    </div>

    @if (loading()) {
      <div class="p-4 text-center">Carregando catálogo…</div>
    } @else {
      @for (dim of dimensions(); track dim) {
        <p-card [header]="dimLabel(dim)" styleClass="mb-3">
          <div class="catalog-list">
            @for (item of byDimension()[dim]; track item.id) {
              <div class="catalog-item" [class.catalog-item--discontinued]="item.is_discontinued">
                <div class="catalog-item__meta">
                  <span class="catalog-item__ref">{{ item.ref_code }}</span>
                  @if (item.is_custom) {
                    <p-tag value="Custom" severity="info" />
                  }
                  @if (item.is_discontinued) {
                    <p-tag value="Descontinuado" severity="secondary" />
                  }
                </div>
                <div class="catalog-item__name">{{ item.name }}</div>
                @if (item.objective) {
                  <div class="catalog-item__obj text-sm text-color-secondary">{{ item.objective }}</div>
                }
                @if (canManage() && !item.is_discontinued) {
                  <div class="catalog-item__actions mt-2">
                    <p-button
                      icon="pi pi-pencil"
                      [text]="true"
                      size="small"
                      (onClick)="openEdit(item)"
                      pTooltip="Editar"
                    />
                  </div>
                }
              </div>
            }
          </div>
        </p-card>
      }

      @if (items().length === 0) {
        <p-card>
          <p class="text-center text-color-secondary p-4">
            Catálogo vazio. Adote o seed ISO 27001:2022 ou crie itens personalizados.
          </p>
        </p-card>
      }
    }

    <!-- Dialog de criação/edição -->
    <p-dialog
      [header]="editingItem() ? 'Editar item' : 'Novo item personalizado'"
      [(visible)]="dialogVisible"
      [style]="{ width: '560px' }"
      [modal]="true"
    >
      <form [formGroup]="form" class="flex flex-col gap-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block font-semibold mb-1">Código *</label>
            <input pInputText formControlName="ref_code" placeholder="Ex.: A.5.1" class="w-full" />
          </div>
          <div>
            <label class="block font-semibold mb-1">Dimensão *</label>
            <p-select
              [options]="dimensionOptions"
              formControlName="dimension"
              optionLabel="label"
              optionValue="value"
              styleClass="w-full"
            />
          </div>
        </div>

        <div>
          <label class="block font-semibold mb-1">Nome *</label>
          <input pInputText formControlName="name" placeholder="Nome do controle ou cláusula" class="w-full" />
        </div>

        <div>
          <label class="block font-semibold mb-1">Tema (Anexo A)</label>
          <p-select
            [options]="themeOptions"
            formControlName="theme"
            optionLabel="label"
            optionValue="value"
            placeholder="Selecione…"
            [showClear]="true"
            styleClass="w-full"
          />
        </div>

        <div>
          <label class="block font-semibold mb-1">Objetivo</label>
          <textarea
            pTextarea
            formControlName="objective"
            rows="2"
            class="w-full"
            placeholder="Objetivo do controle…"
          ></textarea>
        </div>
      </form>

      <ng-template pTemplate="footer">
        <p-button label="Cancelar" severity="secondary" (onClick)="closeDialog()" />
        <p-button
          [label]="editingItem() ? 'Salvar' : 'Criar'"
          icon="pi pi-check"
          (onClick)="saveItem()"
          [loading]="saving()"
          [disabled]="form.invalid"
        />
      </ng-template>
    </p-dialog>
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .catalog-list { display: flex; flex-direction: column; gap: .5rem; }
    .catalog-item { border: 1px solid var(--surface-border); border-radius: 6px; padding: .75rem; }
    .catalog-item--discontinued { opacity: .55; }
    .catalog-item__meta { display: flex; gap: .5rem; align-items: center; margin-bottom: .25rem; }
    .catalog-item__ref { font-weight: 700; font-size: .85rem; }
    .catalog-item__actions { display: flex; gap: .25rem; }
  `],
})
export class GapCatalogPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);
  private fb = inject(NonNullableFormBuilder);

  items = signal<GapCatalogItem[]>([]);
  loading = signal(true);
  adopting = signal(false);
  saving = signal(false);
  editingItem = signal<GapCatalogItem | null>(null);
  dialogVisible = false;

  canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_gap'));

  dimensionOptions = DIMENSION_OPTIONS;
  themeOptions = THEME_OPTIONS;

  form = this.fb.group({
    ref_code: ['', Validators.required],
    dimension: ['annex_a' as string, Validators.required],
    name: ['', Validators.required],
    theme: [null as string | null],
    objective: [''],
  });

  dimensions = computed<GapDimension[]>(() => {
    const dims = new Set(this.items().map((i) => i.dimension as GapDimension));
    return (['clause', 'annex_a'] as GapDimension[]).filter((d) => dims.has(d));
  });

  byDimension = computed(() => {
    const map: Record<string, GapCatalogItem[]> = {};
    for (const item of this.items()) {
      (map[item.dimension] ??= []).push(item);
    }
    return map;
  });

  ngOnInit() {
    this.load();
  }

  private load() {
    this.loading.set(true);
    this.api.get<GapCatalogItem[]>('/gap/catalog').subscribe({
      next: (items) => { this.items.set(items); this.loading.set(false); },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro ao carregar catálogo', detail: e.message });
        this.loading.set(false);
      },
    });
  }

  adoptSeed() {
    this.adopting.set(true);
    this.api.post<unknown>('/gap/catalog/adopt', { seed_version: '2022.1' }).subscribe({
      next: () => {
        this.msg.add({ severity: 'success', summary: 'Catálogo atualizado', detail: 'Itens do seed 2022.1 adotados.' });
        this.adopting.set(false);
        this.load();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.adopting.set(false);
      },
    });
  }

  openNew() {
    this.editingItem.set(null);
    this.form.reset({ ref_code: '', dimension: 'annex_a', name: '', theme: null, objective: '' });
    this.dialogVisible = true;
  }

  openEdit(item: GapCatalogItem) {
    this.editingItem.set(item);
    this.form.patchValue({
      ref_code: item.ref_code,
      dimension: item.dimension,
      name: item.name,
      theme: item.theme,
      objective: item.objective ?? '',
    });
    this.dialogVisible = true;
  }

  closeDialog() {
    this.dialogVisible = false;
    this.editingItem.set(null);
  }

  saveItem() {
    if (this.form.invalid) return;
    this.saving.set(true);
    const body = this.form.getRawValue();
    const editing = this.editingItem();

    const req = editing
      ? this.api.patch<GapCatalogItem>(`/gap/catalog/${editing.id}`, body)
      : this.api.post<GapCatalogItem>('/gap/catalog', body);

    req.subscribe({
      next: (item) => {
        if (editing) {
          this.items.update((list) => list.map((i) => (i.id === item.id ? item : i)));
        } else {
          this.items.update((list) => [...list, item]);
        }
        this.msg.add({ severity: 'success', summary: editing ? 'Atualizado' : 'Criado', detail: item.name });
        this.saving.set(false);
        this.closeDialog();
      },
      error: (e) => {
        this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message });
        this.saving.set(false);
      },
    });
  }

  dimLabel(dim: GapDimension): string {
    return DIM_LABELS[dim] ?? dim;
  }
}
