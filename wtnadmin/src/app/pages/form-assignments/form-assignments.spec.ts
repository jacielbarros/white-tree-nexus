import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of } from 'rxjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { AuthStore } from '@app/core/auth.store';
import { FormAssignment } from '@app/core/models';
import { FormAssignmentsPage } from './form-assignments';

const ASSIGNMENT: FormAssignment = {
  id: 'asgn-1',
  template_id: 'tpl-1',
  kind: 'diagnostic',
  title: 'Diagnóstico Base',
  fields_snapshot: [],
  status: 'pending',
  respondent_user_id: 'user-2',
  respondent_email: null,
  deadline_at: null,
  overdue: false,
  answers: {},
  current_version_id: null,
  claimed_at: null,
  submitted_at: null,
  signed_at: null,
  instructions: null,
};

function apiStub() {
  return {
    listAssignments: vi.fn(() => of([ASSIGNMENT])),
    listTemplates: vi.fn(() => of([])),
    listUsers: vi.fn(() => of([])),
    createAssignment: vi.fn(() => of({ ...ASSIGNMENT, id: 'asgn-2', status: 'pending' })),
    getAssignment: vi.fn(() => of(ASSIGNMENT)),
    claimAssignment: vi.fn(() => of({ ...ASSIGNMENT, status: 'in_progress' })),
    saveAnswers: vi.fn(() => of(ASSIGNMENT)),
    submitAssignment: vi.fn(() => of({ ...ASSIGNMENT, status: 'submitted' })),
    returnAssignment: vi.fn(() => of({ ...ASSIGNMENT, status: 'in_progress' })),
    cancelAssignment: vi.fn(() => of({ ...ASSIGNMENT, status: 'cancelled' })),
    remindAssignment: vi.fn(() => of(undefined)),
    signAssignment: vi.fn(() => of({ id: 'sig-1', signer_role: 'filler', signer_name: 'Test', signed_at: '', content_hash: 'abc', level: 'advanced', otp_verified: false })),
    getAssignmentEvents: vi.fn(() => of([])),
    getAssignmentSignatures: vi.fn(() => of([])),
    verifyAssignment: vi.fn(() => of({ valid: true, content_hash: 'abc123' })),
    getSignaturePolicy: vi.fn(() => of({ require_assigner_countersignature: false })),
    updateSignaturePolicy: vi.fn(() => of({ require_assigner_countersignature: true })),
  };
}

function storeStub(role = 'org_admin') {
  return {
    activeOrgId: vi.fn(() => 'org-1'),
    currentRole: vi.fn(() => role),
  };
}

describe('FormAssignmentsPage', () => {
  let fixture: ComponentFixture<FormAssignmentsPage>;
  let component: FormAssignmentsPage;
  let api: ReturnType<typeof apiStub>;

  beforeEach(async () => {
    api = apiStub();
    await TestBed.configureTestingModule({
      imports: [FormAssignmentsPage],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: api },
        { provide: AuthStore, useValue: storeStub() },
        MessageService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FormAssignmentsPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('carrega lista de atribuições no init', () => {
    expect(api.listAssignments).toHaveBeenCalled();
    expect(component['assignments']().length).toBe(1);
  });

  it('canAssign é true para org_admin', () => {
    expect(component['canAssign']()).toBe(true);
  });

  it('selecionar atribuição carrega eventos', () => {
    component['select'](ASSIGNMENT);
    expect(api.getAssignmentEvents).toHaveBeenCalledWith('asgn-1');
  });

  it('selecionar signed carrega assinaturas', () => {
    const signed: FormAssignment = { ...ASSIGNMENT, status: 'signed' };
    component['select'](signed);
    expect(api.getAssignmentSignatures).toHaveBeenCalledWith('asgn-1');
  });

  it('remind chama API', () => {
    component['remind']('asgn-1');
    expect(api.remindAssignment).toHaveBeenCalledWith('asgn-1');
  });

  it('cancelAssignment chama API', () => {
    component['cancelAssignment']('asgn-1');
    expect(api.cancelAssignment).toHaveBeenCalledWith('asgn-1');
  });

  it('verify chama verifyAssignment', () => {
    component['verify']('asgn-1');
    expect(api.verifyAssignment).toHaveBeenCalledWith('asgn-1');
  });

  it('carrega a política de assinatura no init', () => {
    expect(api.getSignaturePolicy).toHaveBeenCalled();
    expect(component['policyDouble']()).toBe(false);
  });

  it('togglePolicy atualiza a política', () => {
    component['togglePolicy'](true);
    expect(api.updateSignaturePolicy).toHaveBeenCalledWith({ require_assigner_countersignature: true });
    expect(component['policyDouble']()).toBe(true);
  });
});
