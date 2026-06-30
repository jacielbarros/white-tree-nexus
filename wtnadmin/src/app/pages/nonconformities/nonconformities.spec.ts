import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { NCSummary, Role } from '@app/core/models';
import { NonconformitiesPage } from './nonconformities';

const NC: NCSummary = {
  id: 'nc-1', code: 'NC-0001', origin: 'incident', title: 'Falha de backup', severity: 'maior',
  status: 'open', source_finding_id: null, target_type: null, target_id: null,
};

function apiStub() {
  return {
    get: vi.fn((_path: string) => of([NC])),
    post: vi.fn((_path: string, _body: unknown) => of(NC)),
  };
}

function setup(role: Role): { fixture: ComponentFixture<NonconformitiesPage>; component: NonconformitiesPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [NonconformitiesPage],
    providers: [MessageService, provideRouter([]), { provide: ApiService, useValue: api }, { provide: AuthStore, useValue: { currentRole: () => role } }],
  });
  const fixture = TestBed.createComponent(NonconformitiesPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('NonconformitiesPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('lists nonconformities', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.get).toHaveBeenCalledWith('/nonconformities');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('NC-0001');
    expect(text).toContain('Maior');
  });

  it('passes filters as query params', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { filterStatus: string; filterOverdue: boolean; load(): void };
    c.filterStatus = 'in_progress';
    c.filterOverdue = true;
    c.load();
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('status=in_progress'));
    expect(api.get).toHaveBeenCalledWith(expect.stringContaining('overdue=true'));
  });

  it('creates a nonconformity', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { newTitle: string; newDescription: string; create(e: Event): void };
    c.newTitle = 'Nova';
    c.newDescription = 'desvio';
    c.create(new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/nonconformities', expect.objectContaining({ title: 'Nova' }));
  });

  it('hides creation form for non-managers', () => {
    const { fixture } = setup('client');
    expect((fixture.nativeElement as HTMLElement).querySelector('.stack-form')).toBeNull();
  });
});
