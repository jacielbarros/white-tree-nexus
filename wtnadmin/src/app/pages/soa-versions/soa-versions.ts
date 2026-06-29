import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { DialogModule } from 'primeng/dialog';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { hasPermission } from '@app/core/permissions';
import { Soa, SoaVersion } from '@app/core/models';

@Component({
  selector: 'app-soa-versions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, FormsModule, RouterLink, ButtonModule, CardModule, DialogModule, SelectModule, TagModule],
  template: `
    <div class="page-header">
      <h2>SoA — Versões e Emissão</h2>
      <a routerLink="../soa"><p-button label="Voltar à matriz" icon="pi pi-table" severity="secondary" /></a>
    </div>

    @if (loading()) {
      <div class="p-4 text-center">Carregando…</div>
    } @else if (!soa()) {
      <p-card><p class="text-center p-4">Sem SoA. <a routerLink="../soa">Consolide a partir do Gap Analysis.</a></p></p-card>
    } @else {
      <p-card header="Documento Controlado" styleClass="mb-3">
        <div class="flex items-center gap-3 flex-wrap">
          <span>Status do rascunho: <p-tag [value]="soa()!.draft_status" /></span>
          @if (canManage() && soa()!.draft_status === 'draft') {
            <p-button label="Enviar para revisão" icon="pi pi-send" size="small" (onClick)="submitReview()" [loading]="busy()" />
          }
          @if (canApprove() && soa()!.draft_status === 'in_review') {
            <p-button label="Aprovar e emitir" icon="pi pi-check" size="small" (onClick)="showApprove()" [loading]="busy()" />
          }
        </div>
        @if (soa()!.readiness; as r) {
          <div class="kind-hint mt-2" [class.is-normative]="r.kind === 'normative'">
            Ao aprovar agora, a versão será emitida como
            <b>{{ r.kind === 'normative' ? 'SoA normativa (6.1.3 d)' : 'Pré-SoA (consolidação do Gap)' }}</b>.
            @if (r.kind !== 'normative' && r.pending_for_normative.length) {
              <ul class="kind-hint__pending">
                @for (p of r.pending_for_normative; track p) { <li>{{ p }}</li> }
              </ul>
            }
          </div>
        }
        @if (incomplete().length) {
          <div class="incomplete-box mt-2">
            <b>SoA incompleta</b> — controles pendentes (sem razão de inclusão ou justificativa):
            {{ incomplete().join(', ') }}
          </div>
        }
      </p-card>

      <p-card header="Versões emitidas">
        @if (versions().length === 0) {
          <p class="text-color-secondary">Nenhuma versão emitida ainda.</p>
        } @else {
          @for (v of versions(); track v.id) {
            <div class="version-row">
              <div class="version-row__meta">
                <span class="font-semibold">{{ v.identifier }} v{{ v.version_number }}</span>
                <p-tag [value]="v.status" [severity]="v.is_superseded ? 'secondary' : 'success'" />
                <p-tag [value]="kindLabel(v.kind)" [severity]="v.kind === 'normative' ? 'success' : 'warn'" />
                @if (v.signed) { <p-tag value="Assinada" severity="info" /> }
                <span class="text-sm text-color-secondary">{{ v.classification }}</span>
              </div>
              <div class="text-sm text-color-secondary">
                {{ v.change_nature }} · {{ v.created_at | date:'dd/MM/yyyy HH:mm' }}
              </div>
              <p-button label="Exportar PDF" icon="pi pi-download" size="small" [text]="true"
                (onClick)="exportVersion(v)" />
            </div>
          }
        }
      </p-card>

      <p-dialog header="Aprovar e emitir SoA" [(visible)]="approveVisible" [style]="{ width: '460px' }" [modal]="true">
        <div class="flex flex-col gap-3">
          <div>
            <label class="block font-semibold mb-1">Classificação</label>
            <p-select [options]="classificationOptions" [(ngModel)]="approveClassification"
              optionLabel="label" optionValue="value" styleClass="w-full" />
          </div>
          <div>
            <label class="block font-semibold mb-1">Natureza da alteração</label>
            <input class="w-full p-2" [(ngModel)]="approveNature" />
          </div>
          <div class="flex items-center gap-2">
            <input type="checkbox" [(ngModel)]="approveSign" id="sign" />
            <label for="sign">Assinar eletronicamente (avançada)</label>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <p-button label="Cancelar" severity="secondary" (onClick)="approveVisible = false" />
          <p-button label="Aprovar" icon="pi pi-check" (onClick)="approve()" [loading]="busy()" />
        </ng-template>
      </p-dialog>
    }
  `,
  styles: [`
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .version-row { border: 1px solid var(--surface-border); border-radius: 6px; padding: .6rem .75rem; margin-bottom: .5rem; }
    .version-row__meta { display: flex; gap: .5rem; align-items: center; margin-bottom: .2rem; }
    .incomplete-box { border: 1px solid var(--red-300, #f5a9a9); background: var(--red-50, #fff0f0); border-radius: 6px; padding: .6rem .75rem; font-size: .85rem; }
    .kind-hint { border: 1px solid var(--orange-300, #f0a868); background: var(--orange-50, #fff5eb); border-radius: 6px; padding: .6rem .75rem; font-size: .85rem; }
    .kind-hint.is-normative { border-color: var(--green-300, #86dba8); background: var(--green-50, #f0fbf4); }
    .kind-hint__pending { margin: .25rem 0 0; padding-left: 1.1rem; }
  `],
})
export class SoaVersionsPage implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthStore);
  private msg = inject(MessageService);

  soa = signal<Soa | null>(null);
  versions = signal<SoaVersion[]>([]);
  loading = signal(true);
  busy = signal(false);
  incomplete = signal<string[]>([]);

  approveVisible = false;
  approveClassification = 'uso_interno';
  approveNature = 'Emissão inicial';
  approveSign = false;

  classificationOptions = [
    { label: 'Público', value: 'publico' },
    { label: 'Uso interno', value: 'uso_interno' },
    { label: 'Confidencial', value: 'confidencial' },
    { label: 'Restrito', value: 'restrito' },
  ];

  canManage = computed(() => hasPermission(this.auth.currentRole(), 'manage_soa'));
  canApprove = computed(() => hasPermission(this.auth.currentRole(), 'approve_soa'));

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.api.get<Soa>('/soa').subscribe({
      next: (s) => { this.soa.set(s); this.loadVersions(); },
      error: () => { this.soa.set(null); this.loading.set(false); },
    });
  }

  private loadVersions() {
    this.api.get<SoaVersion[]>('/soa/versions').subscribe({
      next: (v) => { this.versions.set(v); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  submitReview() {
    this.busy.set(true);
    this.api.post<{ status: string }>('/soa/submit-review', {}).subscribe({
      next: () => { this.busy.set(false); this.msg.add({ severity: 'success', summary: 'Enviada para revisão' }); this.load(); },
      error: (e) => { this.busy.set(false); this.msg.add({ severity: 'error', summary: 'Erro', detail: e.error?.detail ?? e.message }); },
    });
  }

  showApprove() {
    this.approveClassification = 'uso_interno';
    this.approveNature = this.versions().length ? 'Revisão' : 'Emissão inicial';
    this.approveSign = false;
    this.approveVisible = true;
  }

  approve() {
    this.busy.set(true);
    this.incomplete.set([]);
    this.api.post<SoaVersion>('/soa/approve', {
      classification: this.approveClassification,
      change_nature: this.approveNature,
      sign: this.approveSign,
    }).subscribe({
      next: () => {
        this.busy.set(false);
        this.approveVisible = false;
        this.msg.add({ severity: 'success', summary: 'SoA emitida' });
        this.load();
      },
      error: (e) => {
        this.busy.set(false);
        const detail = e.error?.detail;
        if (e.status === 422 && detail?.incomplete) {
          this.incomplete.set(detail.incomplete);
          this.approveVisible = false;
          this.msg.add({ severity: 'warn', summary: 'SoA incompleta', detail: 'Complete os controles pendentes.' });
        } else {
          this.msg.add({ severity: 'error', summary: 'Erro', detail: typeof detail === 'string' ? detail : e.message });
        }
      },
    });
  }

  kindLabel(kind: string): string {
    return kind === 'normative' ? 'Normativa' : 'Pré-SoA';
  }

  exportVersion(v: SoaVersion) {
    this.api.getBlob(`/soa/versions/${v.id}/export`).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `SoA-v${v.version_number}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: (e) => this.msg.add({ severity: 'error', summary: 'Erro ao exportar', detail: e.message }),
    });
  }
}
