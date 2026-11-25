/**008 explicit acknowledgement and stable retry identity prevent accidental duplicate decisions. */
import React from 'react';
import '@testing-library/jest-dom/vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {afterEach,beforeEach,test,expect,vi} from 'vitest';
import {ResendDialog} from '../../src/components/notifications/ResendDialog';
import {notificationsApi} from '../../src/lib/api/notifications';
vi.mock('../../src/lib/api/notifications',()=>({notificationsApi:{resend:vi.fn()}}));
beforeEach(()=>{HTMLDialogElement.prototype.showModal=function(){this.open=true;};HTMLDialogElement.prototype.close=function(){this.open=false;};});
afterEach(()=>{cleanup();vi.clearAllMocks();});
test('only an explicit reason and possible-duplicate acknowledgement permit a resend',async()=>{
 /**Opening the dialog is read-only; the primary action stays unavailable until both required decisions exist. */
 render(<ResendDialog deliveryId="00000000-0000-0000-0000-000000000008" onClose={vi.fn()} onSent={vi.fn()}/>);expect(notificationsApi.resend).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Autorizar reenvío'})).toBeDisabled();fireEvent.change(screen.getByLabelText('Motivo del reenvío'),{target:{value:'Revisado'}});expect(screen.getByRole('button',{name:'Autorizar reenvío'})).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));expect(screen.getByRole('button',{name:'Autorizar reenvío'})).toBeEnabled();
});
test('uncertain response preserves the exact decision and key on retry',async()=>{
 /**A retry sends no fresh key and cannot silently change its already submitted rationale. */
 vi.mocked(notificationsApi.resend).mockRejectedValueOnce(new Error('synthetic network loss')).mockResolvedValueOnce({delivery:{id:'new-delivery'}} as never);const sent=vi.fn();render(<ResendDialog deliveryId="original" onClose={vi.fn()} onSent={sent}/>);fireEvent.change(screen.getByLabelText('Motivo del reenvío'),{target:{value:'Revisado'}});fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByRole('button',{name:'Autorizar reenvío'}));await screen.findByRole('alert');expect(screen.getByLabelText('Motivo del reenvío')).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Reintentar misma decisión'}));await waitFor(()=>expect(sent).toHaveBeenCalledWith('new-delivery'));expect(vi.mocked(notificationsApi.resend).mock.calls[0]).toEqual(vi.mocked(notificationsApi.resend).mock.calls[1]);
});
