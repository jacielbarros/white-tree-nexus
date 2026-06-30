import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { ManagementReviewSummary, Role } from '@app/core/models';
import { ManagementReviewsPage } from './management-reviews';

const REVIEW: ManagementReviewSummary = { id: 'mr-1', title: 'Análise Crítica 2026/1', review_date: '2026-06-30', draft_status: 'draft', current_version_id: null };

function apiStub() {
  return {
    get: vi.fn((_p: string) => of([REVIEW])),
    post: vi.fn((_p: string, _b: unknown) => of(REVIEW)),
  };
}

function setup(role: Role): { fixture: ComponentFixture<ManagementReviewsPage>; component: ManagementReviewsPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [ManagementReviewsPage],
    providers: [MessageService, provideRouter([]), { provide: ApiService, useValue: api }, { provide: AuthStore, useValue: { currentRole: () => role } }],
  });
  const fixture = TestBed.createComponent(ManagementReviewsPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('ManagementReviewsPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('lists reviews', () => {
    const { fixture, api } = setup('org_admin');
    expect(api.get).toHaveBeenCalledWith('/management-reviews');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Análise Crítica 2026/1');
  });

  it('creates a review', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { newTitle: string; create(e: Event): void };
    c.newTitle = 'Nova ata';
    c.create(new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/management-reviews', expect.objectContaining({ title: 'Nova ata' }));
  });

  it('hides creation form for non-managers', () => {
    const { fixture } = setup('client');
    expect((fixture.nativeElement as HTMLElement).querySelector('.inline-form')).toBeNull();
  });
});
