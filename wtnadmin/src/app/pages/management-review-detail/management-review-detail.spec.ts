import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { ManagementReviewDetail, Role } from '@app/core/models';
import { ManagementReviewDetailPage } from './management-review-detail';

const DETAIL: ManagementReviewDetail = {
  id: 'mr-1', title: 'Ata', review_date: '2026-06-30', draft_status: 'in_review', current_version_id: null,
  inputs: { 'Resultados de auditoria': 'ok' }, outputs: { 'Decisões': 'manter' }, readiness: { can_approve: true },
};

function apiStub() {
  return {
    get: vi.fn((path: string) => of(path.includes('/versions') ? [] : DETAIL)),
    post: vi.fn((_p: string, _b: unknown) => of({})),
    put: vi.fn((_p: string, _b: unknown) => of({})),
    getBlob: vi.fn((_p: string) => of(new Blob(['%PDF'], { type: 'application/pdf' }))),
  };
}

function setup(role: Role): { fixture: ComponentFixture<ManagementReviewDetailPage>; component: ManagementReviewDetailPage; api: ReturnType<typeof apiStub> } {
  TestBed.resetTestingModule();
  const api = apiStub();
  TestBed.configureTestingModule({
    imports: [ManagementReviewDetailPage],
    providers: [
      MessageService,
      provideRouter([]),
      { provide: ApiService, useValue: api },
      { provide: AuthStore, useValue: { currentRole: () => role } },
      { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => 'mr-1' } } } },
    ],
  });
  const fixture = TestBed.createComponent(ManagementReviewDetailPage);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('ManagementReviewDetailPage', () => {
  beforeEach(() => TestBed.resetTestingModule());

  it('loads the review with inputs/outputs', () => {
    const { fixture } = setup('org_admin');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ata');
    expect(text).toContain('Aprovar ata');
  });

  it('approves with sign flag', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { sign: boolean; approve(r: ManagementReviewDetail, e: Event): void };
    c.sign = true;
    c.approve(DETAIL, new Event('submit'));
    expect(api.post).toHaveBeenCalledWith('/management-reviews/mr-1/approve', expect.objectContaining({ sign: true }));
  });

  it('exports a version PDF', () => {
    const { component, api } = setup('org_admin');
    const c = component as unknown as { exportPdf(v: { id: string; version_number: number }): void };
    c.exportPdf({ id: 'v-1', version_number: 1 });
    expect(api.getBlob).toHaveBeenCalledWith('/management-reviews/mr-1/versions/v-1/export');
  });
});
