import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { provideRouter } from '@angular/router';
import { MessageService } from 'primeng/api';
import { of, throwError } from 'rxjs';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ApiService } from '@app/core/api.service';
import { FormAssignment } from '@app/core/models';
import { FormRespondPage } from './form-respond';

const PENDING: FormAssignment = {
  id: 'asgn-1', template_id: 'tpl-1', kind: 'diagnostic', title: 'Formulário Externo',
  fields_snapshot: [{ label: 'Nome', key: 'nome', type: 'text', required: true }],
  status: 'pending', respondent_user_id: null, respondent_email: 'ext@exemplo.com',
  deadline_at: null, overdue: false, answers: {}, current_version_id: null,
  claimed_at: null, submitted_at: null, signed_at: null, instructions: 'Preencha com atenção.',
};

function makeApi() {
  return {
    getFormByToken: vi.fn(() => of(PENDING)),
    claimByToken: vi.fn(() => of({ ...PENDING, status: 'in_progress' })),
    saveAnswersByToken: vi.fn(() => of({ ...PENDING, status: 'in_progress' })),
    submitByToken: vi.fn(() => of({ ...PENDING, status: 'submitted' })),
    requestOtpByToken: vi.fn(() => of(undefined)),
    signByToken: vi.fn(() => of({ id: 'sig-1', signer_role: 'filler', signer_name: 'João', signed_at: '', content_hash: 'hash123', level: 'advanced', otp_verified: true })),
  };
}

describe('FormRespondPage', () => {
  let fixture: ComponentFixture<FormRespondPage>;
  let component: FormRespondPage;
  let api: ReturnType<typeof makeApi>;

  beforeEach(async () => {
    api = makeApi();
    await TestBed.configureTestingModule({
      imports: [FormRespondPage],
      providers: [
        provideRouter([]),
        { provide: ApiService, useValue: api },
        MessageService,
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: { get: () => 'abc123token' } } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FormRespondPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('resolve o token e exibe stage=claim para status pending', () => {
    expect(api.getFormByToken).toHaveBeenCalledWith('abc123token');
    expect(component['stage']()).toBe('claim');
  });

  it('claim muda stage para fill', () => {
    component['claim']();
    expect(api.claimByToken).toHaveBeenCalledWith('abc123token');
    expect(component['stage']()).toBe('fill');
  });

  it('submit muda stage para sign_otp', () => {
    component['stage'].set('fill');
    component['submit']();
    expect(api.saveAnswersByToken).toHaveBeenCalled();
    expect(api.submitByToken).toHaveBeenCalled();
    expect(component['stage']()).toBe('sign_otp');
  });

  it('requestOtp seta otpSent', () => {
    component['requestOtp']();
    expect(api.requestOtpByToken).toHaveBeenCalledWith('abc123token');
    expect(component['otpSent']()).toBe(true);
  });

  it('signWithOtp completa e vai para done', () => {
    component['signerName'] = 'João';
    component['otpCode'] = '123456';
    component['signWithOtp']();
    expect(api.signByToken).toHaveBeenCalledWith('abc123token', '123456', 'João');
    expect(component['stage']()).toBe('done');
    expect(component['contentHash']()).toBe('hash123');
  });

  it('exibe error stage em token inválido (404)', async () => {
    api.getFormByToken.mockReturnValue(throwError(() => ({ status: 404 })));
    component.ngOnInit();
    expect(component['stage']()).toBe('error');
  });
});
