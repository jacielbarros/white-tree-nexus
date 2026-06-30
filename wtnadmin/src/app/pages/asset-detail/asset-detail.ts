import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule, NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectModule } from 'primeng/select';
import { TextareaModule } from 'primeng/textarea';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { EvidencePanel } from '@app/shared/evidence-panel/evidence-panel';
import {
  AssetItem,
  AssetItemDetail,
  AssetItemEvent,
  AssetRelationshipType,
  AssetType,
  CiaLevel,
} from '@app/core/models';
import {
  ASSET_TYPE_LABELS,
  CIA_LABELS,
  RECORD_STATUS_LABELS,
  RELATIONSHIP_TYPE_LABELS,
  REVIEW_STATUS_LABELS,
  SCOPE_STATUS_LABELS,
} from '@app/pages/assets/asset-labels';

interface Option<T = string> { label: string; value: T; }
interface MemberRow { user_id: string; full_name: string; email: string; }
interface GapCatalogRow { id: string; ref_code: string; name: string; }

const FUTURE_SECTIONS = ['Ameaças vinculadas', 'Vulnerabilidades vinculadas', 'Riscos vinculados', 'Controles relacionados', 'Evidências'];

@Component({
  selector: 'app-asset-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    SlicePipe, RouterLink, FormsModule, ReactiveFormsModule, ButtonModule, DialogModule,
    InputTextModule, SelectModule, TextareaModule, EvidencePanel,
  ],
  template: `
    @if (detail(); as d) {
      <header class="wtn-page-header">
        <div>
          <a routerLink="../../assets" class="back">← Ativos e Processos</a>
          <h1 class="wtn-page-title">{{ d.item.name }} <span class="code">{{ d.item.code }}</span></h1>
          <p class="wtn-page-desc">{{ typeLabel(d.item.item_type) }} · {{ recordLabel(d.item.record_status) }}</p>
        </div>
        <div class="wtn-page-actions">
          @if (canManage()) {
            <p-button label="Editar" icon="pi pi-pencil" severity="secondary" (onClick)="openEdit()" />
            @if (d.item.record_status !== 'archived') {
              <p-button label="Arquivar" icon="pi pi-inbox" severity="secondary" [text]="true" (onClick)="archiveVisible.set(true)" />
            }
          }
        </div>
      </header>

      <div class="detail-grid">
        <!-- Dados gerais -->
        <article class="wtn-card pad">
          <div class="wtn-card-title">Dados gerais</div>
          <dl class="kv">
            <dt>Escopo</dt><dd><span [class]="'wtn-tag ' + scopeClass(d.item.scope_status)">{{ scopeLabel(d.item.scope_status) }}</span></dd>
            <dt>Área / unidade</dt><dd>{{ d.item.business_unit || '—' }}</dd>
            <dt>Localização</dt><dd>{{ d.item.location || '—' }}</dd>
            <dt>Descrição</dt><dd>{{ d.item.description || '—' }}</dd>
            @if (d.item.scope_status === 'out_of_scope') {
              <dt>Justificativa de exclusão</dt><dd>{{ d.item.scope_justification || '—' }}</dd>
            }
            <dt>Dados pessoais</dt><dd>{{ d.item.has_personal_data ? 'Sim' : 'Não' }}</dd>
            <dt>Dados sensíveis</dt><dd>{{ d.item.has_sensitive_data ? 'Sim' : 'Não' }}</dd>
            <dt>Observações LGPD</dt><dd>{{ d.item.compliance_notes || '—' }}</dd>
          </dl>
          @if (d.item.pending_fields.length) {
            <p class="pending">⚠ Pendências: {{ pendingLabel(d.item.pending_fields) }}</p>
          }
        </article>

        <!-- CIA + criticidade -->
        <article class="wtn-card pad">
          <div class="wtn-card-title">Classificação CIA</div>
          <dl class="kv">
            <dt>Confidencialidade</dt><dd>{{ cia(d.item.confidentiality) }}</dd>
            <dt>Integridade</dt><dd>{{ cia(d.item.integrity) }}</dd>
            <dt>Disponibilidade</dt><dd>{{ cia(d.item.availability) }}</dd>
            <dt>Criticidade</dt><dd><strong>{{ cia(d.item.criticality) }}</strong>
              @if (d.item.criticality_is_manual) { <span class="badge">ajuste manual</span> }</dd>
          </dl>
          @if (d.item.criticality_divergent) {
            <p class="pending">⚠ Criticidade ajustada diverge do cálculo automático ({{ cia(d.item.criticality_computed) }}).</p>
          }
        </article>

        <!-- Responsáveis + revisão -->
        <article class="wtn-card pad">
          <div class="wtn-card-title">Responsáveis e revisão</div>
          <dl class="kv">
            <dt>Responsável</dt><dd>{{ memberName(d.item.responsible_user_id) }}</dd>
            <dt>Dono</dt><dd>{{ memberName(d.item.owner_user_id) }}</dd>
            <dt>Custodiante</dt><dd>{{ memberName(d.item.custodian_user_id) }}</dd>
            <dt>Situação de revisão</dt><dd><span [class]="'wtn-tag ' + reviewClass(d.item.review_status)">{{ reviewLabel(d.item.review_status) }}</span></dd>
            <dt>Próxima revisão</dt><dd>{{ d.item.next_review_at ? (d.item.next_review_at | slice:0:10) : '—' }}</dd>
          </dl>
        </article>

        <!-- Relacionamentos -->
        <article class="wtn-card pad span2">
          <div class="wtn-card-title">Relacionamentos</div>
          @if (d.relationships.length) {
            <ul class="rel-list">
              @for (r of d.relationships; track r.id) {
                <li>
                  <span class="rel-dir">{{ r.direction === 'outgoing' ? '→' : '←' }}</span>
                  <span>{{ relLabel(r.relationship_type) }}</span>
                  <strong>{{ r.direction === 'outgoing' ? r.target_name : r.source_name }}</strong>
                  <span class="mono">{{ r.direction === 'outgoing' ? r.target_code : r.source_code }}</span>
                  @if (canManage() && r.direction === 'outgoing') {
                    <button class="link-del" (click)="removeRel(r.id)">remover</button>
                  }
                </li>
              }
            </ul>
          } @else { <p class="muted">Nenhum relacionamento.</p> }
          @if (canManage()) {
            <div class="inline-form">
              <p-select [options]="relTypeOptions" optionLabel="label" optionValue="value" [(ngModel)]="newRelType" placeholder="Tipo" />
              <p-select [options]="targetOptions()" optionLabel="label" optionValue="value" [(ngModel)]="newRelTarget" placeholder="Item de destino" [filter]="true" />
              <p-button label="Relacionar" icon="pi pi-link" size="small" (onClick)="addRel()" [disabled]="!newRelTarget" />
            </div>
          }
        </article>

        <!-- Gaps relacionados -->
        <article class="wtn-card pad span2">
          <div class="wtn-card-title">Gaps relacionados</div>
          @if (d.gap_links.length) {
            <ul class="rel-list">
              @for (g of d.gap_links; track g.id) {
                <li>
                  <span class="mono">{{ g.gap_ref_code }}</span>
                  <strong>{{ g.gap_name }}</strong>
                  @if (g.gap_is_discontinued) { <span class="badge badge--warn">descontinuado</span> }
                  @if (canManage()) { <button class="link-del" (click)="removeGap(g.id)">remover</button> }
                </li>
              }
            </ul>
          } @else { <p class="muted">Nenhum gap vinculado.</p> }
          @if (canManage() && gapCatalog().length) {
            <div class="inline-form">
              <p-select [options]="gapOptions()" optionLabel="label" optionValue="value" [(ngModel)]="newGap" placeholder="Selecione um gap" [filter]="true" />
              <p-button label="Vincular gap" icon="pi pi-link" size="small" (onClick)="addGap()" [disabled]="!newGap" />
            </div>
          }
        </article>

        <!-- Riscos (Feature 012): ameaças/vulnerabilidades/riscos/controles vinculados -->
        <article class="wtn-card pad span2">
          <div class="wtn-card-title">Riscos vinculados</div>
          @if (riskLinks(); as rl) {
            <div class="risk-links">
              <div class="rl-col">
                <h4>Ameaças</h4>
                @for (t of rl.threats; track t.id) { <div class="rl-item">{{ t.code }} · {{ t.name }}</div> }
                @empty { <p class="muted">Nenhuma.</p> }
              </div>
              <div class="rl-col">
                <h4>Vulnerabilidades</h4>
                @for (v of rl.vulnerabilities; track v.id) { <div class="rl-item">{{ v.code }} · {{ v.name }}</div> }
                @empty { <p class="muted">Nenhuma.</p> }
              </div>
              <div class="rl-col">
                <h4>Riscos</h4>
                @for (r of rl.risks; track r.id) {
                  <a class="rl-item rl-link" [routerLink]="['../../risk-detail', r.id]">{{ r.code }} · {{ r.title }}</a>
                }
                @empty { <p class="muted">Nenhum.</p> }
              </div>
              <div class="rl-col">
                <h4>Controles relacionados</h4>
                @for (c of rl.controls; track c.id) { <div class="rl-item">{{ c.custom_control_label || 'Controle do Anexo A' }}</div> }
                @empty { <p class="muted">Nenhum.</p> }
              </div>
            </div>
          } @else { <p class="muted">Carregando vínculos de risco…</p> }
        </article>

        <!-- Evidências transversais (Feature 014) -->
        <article class="wtn-card pad span2">
          <app-evidence-panel [targetType]="'asset'" [targetId]="itemId" [canManage]="canManageEvidence()" title="Evidências do ativo" />
        </article>

        <!-- Histórico -->
        <article class="wtn-card pad span2">
          <div class="wtn-card-title">Histórico de alterações</div>
          @if (history().length) {
            <ul class="timeline">
              @for (e of history(); track e.id) {
                <li>
                  <span class="ev-type">{{ eventLabel(e.event_type) }}</span>
                  <span class="ev-detail">{{ e.field_name ? (e.field_name + ': ' + (e.old_value ?? '—') + ' → ' + (e.new_value ?? '—')) : (e.new_value ?? '') }}</span>
                  @if (e.reason) { <span class="ev-reason">“{{ e.reason }}”</span> }
                  <span class="ev-date">{{ e.occurred_at | slice:0:19 }}</span>
                </li>
              }
            </ul>
          } @else { <p class="muted">Sem histórico.</p> }
        </article>
      </div>

      <!-- Dialog editar -->
      <p-dialog [(visible)]="editVisible" header="Editar item" [modal]="true" [style]="{ width: '680px' }">
        <form [formGroup]="form" class="form-grid">
          <label class="span2">Nome *<input pInputText formControlName="name" /></label>
          <label>Tipo *<p-select [options]="typeOptions" optionLabel="label" optionValue="value" formControlName="item_type" /></label>
          <label>Situação de escopo *<p-select [options]="scopeOptions" optionLabel="label" optionValue="value" formControlName="scope_status" /></label>
          <label>Status do registro<p-select [options]="recordOptions" optionLabel="label" optionValue="value" formControlName="record_status" /></label>
          <label>Área / unidade<input pInputText formControlName="business_unit" /></label>
          <label>Localização<input pInputText formControlName="location" /></label>
          <label>Responsável<p-select [options]="memberOptions()" optionLabel="label" optionValue="value" formControlName="responsible_user_id" [showClear]="true" /></label>
          <label>Dono<p-select [options]="memberOptions()" optionLabel="label" optionValue="value" formControlName="owner_user_id" [showClear]="true" /></label>
          <label>Custodiante<p-select [options]="memberOptions()" optionLabel="label" optionValue="value" formControlName="custodian_user_id" [showClear]="true" /></label>
          <label>Confidencialidade<p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="confidentiality" [showClear]="true" /></label>
          <label>Integridade<p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="integrity" [showClear]="true" /></label>
          <label>Disponibilidade<p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="availability" [showClear]="true" /></label>
          <label class="span2 checks">
            <span><input type="checkbox" formControlName="criticality_is_manual" /> Ajustar criticidade manualmente</span>
            @if (form.value.criticality_is_manual) {
              <p-select [options]="ciaOptions" optionLabel="label" optionValue="value" formControlName="criticality" placeholder="Criticidade" />
            }
          </label>
          <label>Próxima revisão<input type="date" pInputText formControlName="next_review_at" /></label>
          <label>Última revisão<input type="date" pInputText formControlName="last_review_at" /></label>
          <label class="span2 checks">
            <span><input type="checkbox" formControlName="has_personal_data" /> Dados pessoais</span>
            <span><input type="checkbox" formControlName="has_sensitive_data" /> Dados sensíveis</span>
          </label>
          @if (form.value.scope_status === 'out_of_scope') {
            <label class="span2">Justificativa de exclusão *<textarea pTextarea formControlName="scope_justification" rows="2"></textarea></label>
          }
          <label class="span2">Observações LGPD/compliance<textarea pTextarea formControlName="compliance_notes" rows="2"></textarea></label>
          <label class="span2">Justificativa da alteração (obrigatória p/ escopo/criticidade/arquivamento)
            <input pInputText formControlName="reason" placeholder="Motivo da mudança" /></label>
          @if (errorMsg()) { <p class="form-error span2">{{ errorMsg() }}</p> }
        </form>
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" [text]="true" (onClick)="editVisible.set(false)" />
          <p-button label="Salvar" icon="pi pi-check" (onClick)="saveEdit()" [disabled]="form.invalid || saving()" />
        </ng-template>
      </p-dialog>

      <!-- Dialog arquivar -->
      <p-dialog [(visible)]="archiveVisible" header="Arquivar item" [modal]="true" [style]="{ width: '440px' }">
        <p class="muted">O item será arquivado (lógico, reversível). Informe a justificativa.</p>
        <input pInputText [(ngModel)]="archiveReason" placeholder="Justificativa" style="width:100%" />
        @if (errorMsg()) { <p class="form-error">{{ errorMsg() }}</p> }
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" [text]="true" (onClick)="archiveVisible.set(false)" />
          <p-button label="Arquivar" icon="pi pi-inbox" severity="danger" (onClick)="archive()" [disabled]="!archiveReason.trim() || saving()" />
        </ng-template>
      </p-dialog>
    } @else if (loading()) {
      <div class="wtn-card pad"><div class="wtn-skeleton skeleton-line"></div></div>
    } @else {
      <div class="wtn-empty"><div class="wtn-empty-title">Item não encontrado</div></div>
    }
  `,
  styles: [`
    :host { display: block; }
    .back { color: var(--wtn-primary); font-size: 12px; text-decoration: none; }
    .code { font-family: var(--wtn-font-mono); font-size: 14px; color: var(--wtn-muted); font-weight: 500; }
    .detail-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
    .wtn-card { background: var(--wtn-card); border: 1px solid var(--wtn-border); border-radius: var(--wtn-r-lg); }
    .pad { padding: 20px; }
    .span2 { grid-column: 1 / -1; }
    .wtn-card-title { color: var(--wtn-muted); font-size: 11px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 14px; }
    .kv { display: grid; grid-template-columns: 130px 1fr; gap: 8px 12px; margin: 0; font-size: 13px; }
    .kv dt { color: var(--wtn-muted); }
    .kv dd { color: var(--wtn-text); margin: 0; }
    .badge { background: var(--wtn-surface-2); border-radius: var(--wtn-r-pill); font-size: 10px; padding: 2px 8px; margin-left: 6px; color: var(--wtn-text-2); }
    .badge--warn { background: var(--wtn-warning); color: #fff; }
    .pending { color: var(--wtn-warning); font-size: 12.5px; margin: 12px 0 0; }
    .muted { color: var(--wtn-muted); font-size: 13px; }
    .rel-list { list-style: none; padding: 0; margin: 0 0 12px; display: flex; flex-direction: column; gap: 8px; }
    .rel-list li { display: flex; align-items: center; gap: 8px; font-size: 13px; }
    .rel-dir { color: var(--wtn-primary); font-weight: 700; }
    .mono { font-family: var(--wtn-font-mono); font-size: 11.5px; color: var(--wtn-muted); }
    .link-del { background: none; border: none; color: var(--wtn-danger); cursor: pointer; font-size: 11.5px; margin-left: auto; }
    .inline-form { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .risk-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 16px; }
    .rl-col h4 { font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: var(--wtn-muted); margin: 0 0 8px; }
    .rl-item { font-size: 12.5px; color: var(--wtn-text-2); padding: 4px 0; border-bottom: 1px solid var(--wtn-border); display: block; text-decoration: none; }
    .rl-link { color: var(--wtn-primary); cursor: pointer; }
    .future { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; }
    .future-box { border: 1px dashed var(--wtn-border-strong); border-radius: var(--wtn-r-md); padding: 12px; display: flex; flex-direction: column; gap: 4px; }
    .future-box span { font-size: 12.5px; color: var(--wtn-text-2); font-weight: 600; }
    .future-box em { font-size: 11px; color: var(--wtn-muted); }
    .timeline { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
    .timeline li { display: flex; flex-wrap: wrap; gap: 8px; align-items: baseline; font-size: 12.5px; border-left: 2px solid var(--wtn-surface-2); padding-left: 12px; }
    .ev-type { font-weight: 600; color: var(--wtn-primary); }
    .ev-detail { color: var(--wtn-text-2); }
    .ev-reason { color: var(--wtn-text); font-style: italic; }
    .ev-date { color: var(--wtn-muted); margin-left: auto; font-family: var(--wtn-font-mono); font-size: 11px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
    .form-grid label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--wtn-text-2); }
    .checks { flex-direction: row !important; gap: 18px; align-items: center; }
    .checks span { display: flex; align-items: center; gap: 6px; color: var(--wtn-text); }
    .form-error { color: var(--wtn-danger); font-size: 13px; margin: 8px 0 0; }
    @media (max-width: 900px) { .detail-grid, .form-grid { grid-template-columns: 1fr; } }
  `],
})
export class AssetDetailPage implements OnInit {
  private api = inject(ApiService);
  private msg = inject(MessageService);
  private route = inject(ActivatedRoute);
  private fb = inject(NonNullableFormBuilder);
  private store = inject(AuthStore);

  readonly detail = signal<AssetItemDetail | null>(null);
  readonly history = signal<AssetItemEvent[]>([]);
  readonly members = signal<MemberRow[]>([]);
  readonly gapCatalog = signal<GapCatalogRow[]>([]);
  readonly allItems = signal<AssetItem[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly editVisible = signal(false);
  readonly archiveVisible = signal(false);
  readonly errorMsg = signal<string | null>(null);

  readonly futureSections = FUTURE_SECTIONS;
  readonly riskLinks = signal<{
    threats: { id: string; code: string; name: string }[];
    vulnerabilities: { id: string; code: string; name: string }[];
    risks: { id: string; code: string; title: string; inherent_level_key: string | null }[];
    controls: { id: string; custom_control_label: string | null; gap_catalog_item_id: string | null }[];
  } | null>(null);

  newRelType: AssetRelationshipType = 'uses';
  newRelTarget: string | null = null;
  newGap: string | null = null;
  archiveReason = '';

  protected itemId = '';

  readonly typeOptions: Option<AssetType>[] = (Object.keys(ASSET_TYPE_LABELS) as AssetType[]).map((v) => ({ label: ASSET_TYPE_LABELS[v], value: v }));
  readonly scopeOptions: Option[] = Object.entries(SCOPE_STATUS_LABELS).map(([value, label]) => ({ label, value }));
  readonly recordOptions: Option[] = Object.entries(RECORD_STATUS_LABELS).map(([value, label]) => ({ label, value }));
  readonly ciaOptions: Option[] = Object.entries(CIA_LABELS).map(([value, label]) => ({ label, value }));
  readonly relTypeOptions: Option<AssetRelationshipType>[] = (Object.keys(RELATIONSHIP_TYPE_LABELS) as AssetRelationshipType[]).map((v) => ({ label: RELATIONSHIP_TYPE_LABELS[v], value: v }));

  readonly memberOptions = computed<Option[]>(() => this.members().map((m) => ({ label: `${m.full_name} (${m.email})`, value: m.user_id })));
  readonly targetOptions = computed<Option[]>(() =>
    this.allItems().filter((i) => i.id !== this.itemId).map((i) => ({ label: `${i.code} — ${i.name}`, value: i.id })));
  readonly gapOptions = computed<Option[]>(() => this.gapCatalog().map((g) => ({ label: `${g.ref_code} — ${g.name}`, value: g.id })));

  readonly form = this.fb.group({
    name: ['', Validators.required],
    item_type: ['information_asset' as AssetType, Validators.required],
    scope_status: ['under_analysis' as string, Validators.required],
    record_status: ['active' as string],
    business_unit: [''],
    location: [''],
    responsible_user_id: [null as string | null],
    owner_user_id: [null as string | null],
    custodian_user_id: [null as string | null],
    confidentiality: [null as CiaLevel | null],
    integrity: [null as CiaLevel | null],
    availability: [null as CiaLevel | null],
    criticality: [null as CiaLevel | null],
    criticality_is_manual: [false],
    next_review_at: [''],
    last_review_at: [''],
    has_personal_data: [false],
    has_sensitive_data: [false],
    scope_justification: [''],
    compliance_notes: [''],
    reason: [''],
  });

  ngOnInit(): void {
    this.itemId = this.route.snapshot.paramMap.get('id') ?? '';
    this.load();
    this.api.listUsers().subscribe({ next: (r) => this.members.set(r as unknown as MemberRow[]), error: () => {} });
    this.api.get<GapCatalogRow[]>('/gap/catalog').subscribe({ next: (g) => this.gapCatalog.set(g), error: () => {} });
    this.api.get<AssetItem[]>('/assets').subscribe({ next: (i) => this.allItems.set(i), error: () => {} });
    this.api.get<NonNullable<ReturnType<typeof this.riskLinks>>>(`/risk/assets/${this.itemId}/links`).subscribe({
      next: (l) => this.riskLinks.set(l), error: () => {},
    });
  }

  private load(): void {
    this.loading.set(true);
    this.api.get<AssetItemDetail>(`/assets/${this.itemId}`).subscribe({
      next: (d) => { this.detail.set(d); this.loading.set(false); this.loadHistory(); },
      error: () => this.loading.set(false),
    });
  }

  private loadHistory(): void {
    this.api.get<AssetItemEvent[]>(`/assets/${this.itemId}/history`).subscribe({
      next: (h) => this.history.set([...h].reverse()), error: () => {},
    });
  }

  canManage(): boolean { return hasPermission(this.store.currentRole(), 'manage_asset'); }
  canManageEvidence(): boolean { return hasPermission(this.store.currentRole(), 'manage_evidence'); }

  openEdit(): void {
    const it = this.detail()?.item;
    if (!it) return;
    this.errorMsg.set(null);
    this.form.reset({
      name: it.name, item_type: it.item_type, scope_status: it.scope_status, record_status: it.record_status,
      business_unit: it.business_unit ?? '', location: it.location ?? '',
      responsible_user_id: it.responsible_user_id, owner_user_id: it.owner_user_id, custodian_user_id: it.custodian_user_id,
      confidentiality: it.confidentiality, integrity: it.integrity, availability: it.availability,
      criticality: it.criticality, criticality_is_manual: it.criticality_is_manual,
      next_review_at: it.next_review_at ? it.next_review_at.slice(0, 10) : '',
      last_review_at: it.last_review_at ? it.last_review_at.slice(0, 10) : '',
      has_personal_data: it.has_personal_data, has_sensitive_data: it.has_sensitive_data,
      scope_justification: it.scope_justification ?? '', compliance_notes: it.compliance_notes ?? '', reason: '',
    });
    this.editVisible.set(true);
  }

  saveEdit(): void {
    if (this.form.invalid) return;
    this.saving.set(true);
    this.errorMsg.set(null);
    const v = this.form.getRawValue();
    const payload = { ...v, next_review_at: v.next_review_at || null, last_review_at: v.last_review_at || null };
    this.api.put<AssetItem>(`/assets/${this.itemId}`, payload).subscribe({
      next: () => { this.saving.set(false); this.editVisible.set(false); this.msg.add({ severity: 'success', summary: 'Item atualizado' }); this.load(); },
      error: (e) => { this.saving.set(false); this.errorMsg.set(e.error?.detail ?? 'Falha ao salvar.'); },
    });
  }

  archive(): void {
    this.saving.set(true);
    this.errorMsg.set(null);
    this.api.post(`/assets/${this.itemId}/archive`, { reason: this.archiveReason.trim() }).subscribe({
      next: () => { this.saving.set(false); this.archiveVisible.set(false); this.archiveReason = ''; this.msg.add({ severity: 'success', summary: 'Item arquivado' }); this.load(); },
      error: (e) => { this.saving.set(false); this.errorMsg.set(e.error?.detail ?? 'Falha ao arquivar.'); },
    });
  }

  addRel(): void {
    if (!this.newRelTarget) return;
    this.api.post(`/assets/${this.itemId}/relationships`, { relationship_type: this.newRelType, target_item_id: this.newRelTarget }).subscribe({
      next: () => { this.newRelTarget = null; this.msg.add({ severity: 'success', summary: 'Relacionamento criado' }); this.load(); },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? 'Falha.' }),
    });
  }

  removeRel(id: string): void {
    this.api.delete(`/assets/${this.itemId}/relationships/${id}`).subscribe({
      next: () => { this.msg.add({ severity: 'success', summary: 'Relacionamento removido' }); this.load(); },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? 'Falha.' }),
    });
  }

  addGap(): void {
    if (!this.newGap) return;
    this.api.post(`/assets/${this.itemId}/gap-links`, { gap_catalog_item_id: this.newGap }).subscribe({
      next: () => { this.newGap = null; this.msg.add({ severity: 'success', summary: 'Gap vinculado' }); this.load(); },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? 'Falha.' }),
    });
  }

  removeGap(id: string): void {
    this.api.delete(`/assets/${this.itemId}/gap-links/${id}`).subscribe({
      next: () => { this.msg.add({ severity: 'success', summary: 'Vínculo removido' }); this.load(); },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? 'Falha.' }),
    });
  }

  typeLabel(t: AssetType): string { return ASSET_TYPE_LABELS[t]; }
  scopeLabel(s: string): string { return SCOPE_STATUS_LABELS[s] ?? s; }
  recordLabel(s: string): string { return RECORD_STATUS_LABELS[s] ?? s; }
  reviewLabel(r: string): string { return REVIEW_STATUS_LABELS[r] ?? r; }
  relLabel(r: AssetRelationshipType): string { return RELATIONSHIP_TYPE_LABELS[r]; }
  cia(c: string | null): string { return c ? (CIA_LABELS[c] ?? c) : '—'; }
  memberName(id: string | null): string {
    if (!id) return '—';
    const m = this.members().find((x) => x.user_id === id);
    return m ? m.full_name : '—';
  }
  pendingLabel(fields: string[]): string {
    return fields.map((f) => (f === 'responsible' ? 'responsável' : 'classificação CIA')).join(', ');
  }
  eventLabel(t: string): string {
    const map: Record<string, string> = {
      CREATE: 'Criado', UPDATE: 'Atualizado', SCOPE_CHANGE: 'Mudança de escopo', SCOPE_EXCLUSION: 'Exclusão de escopo',
      CRITICALITY_CHANGE: 'Mudança de criticidade', RESPONSIBLE_CHANGE: 'Mudança de responsável', ARCHIVE: 'Arquivado',
      RELATIONSHIP_ADD: 'Relacionamento adicionado', RELATIONSHIP_REMOVE: 'Relacionamento removido',
      GAP_LINK: 'Gap vinculado', GAP_UNLINK: 'Gap desvinculado',
    };
    return map[t] ?? t;
  }
  scopeClass(s: string): string {
    return s === 'in_scope' ? 'wtn-tag--success' : s === 'out_of_scope' ? 'wtn-tag--neutral' : 'wtn-tag--warning';
  }
  reviewClass(r: string): string {
    return r === 'overdue' ? 'wtn-tag--danger' : r === 'due_soon' ? 'wtn-tag--warning' : r === 'up_to_date' ? 'wtn-tag--success' : 'wtn-tag--neutral';
  }
}
