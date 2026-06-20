import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';

import { ApiService } from '@app/core/api.service';
import { Suggestion } from '@app/core/models';

@Component({
  selector: 'app-context-overview-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CardModule, TableModule, ButtonModule],
  template: `
    <h2>Visão Consolidada</h2>
    <p-card styleClass="mb">
      <pre>{{ overviewText() }}</pre>
    </p-card>
    <p-table [value]="suggestions()">
      <ng-template pTemplate="header"><tr><th>Sugestão</th><th>Motivo</th><th>Ações</th></tr></ng-template>
      <ng-template pTemplate="body" let-row>
        <tr><td>{{ row.id }}</td><td>{{ row.reason }}</td><td><p-button label="Aceitar" size="small" (onClick)="accept(row)" /></td></tr>
      </ng-template>
    </p-table>
  `,
  styles: `
    h2 { margin-top: 0; }
    .mb { display: block; margin-bottom: 1rem; }
    pre { white-space: pre-wrap; font-size: 0.85rem; }
  `,
})
export class ContextOverviewPage implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly overviewText = signal('{}');
  protected readonly suggestions = signal<Suggestion[]>([]);

  ngOnInit(): void { this.load(); }
  private load(): void {
    this.api.getContextOverview().subscribe({ next: (row) => this.overviewText.set(JSON.stringify(row, null, 2)) });
    this.api.listSuggestions().subscribe({ next: (rows) => this.suggestions.set(rows) });
  }
  protected accept(row: Suggestion): void { this.api.acceptSuggestion(row.id).subscribe({ next: () => this.load() }); }
}
