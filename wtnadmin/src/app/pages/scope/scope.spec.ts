import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MessageService } from 'primeng/api';

import { ApiService } from '@app/core/api.service';
import { ScopePage } from './scope';

const mockApi = {
  getScope: vi.fn(() => of({ id: 's', interfaces_dependencies: '', draft_status: 'draft', items: [] })),
  saveScope: vi.fn(() => of({})),
  createScopeItem: vi.fn(() => of({})),
};

interface View {
  scope: { set(v: unknown): void };
  statusView(): { label: string; cls: string };
  addItem(): void;
}

describe('ScopePage', () => {
  let component: ScopePage;
  let view: View;

  beforeEach(async () => {
    mockApi.createScopeItem.mockClear();
    await TestBed.configureTestingModule({
      imports: [ScopePage],
      providers: [MessageService, { provide: ApiService, useValue: mockApi }],
    }).compileComponents();

    const fixture = TestBed.createComponent(ScopePage);
    component = fixture.componentInstance;
    view = component as unknown as View;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('maps draft_status to a status tag', () => {
    view.scope.set({ draft_status: 'in_force', items: [] });
    expect(view.statusView().label).toBe('Em vigor');
    expect(view.statusView().cls).toBe('wtn-tag--success');
    view.scope.set({ draft_status: 'in_review', items: [] });
    expect(view.statusView().label).toBe('Em revisão');
  });

  it('does not add an item without a description', () => {
    view.addItem();
    expect(mockApi.createScopeItem).not.toHaveBeenCalled();
  });
});
