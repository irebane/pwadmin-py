/* Shared account → character picker used by Roles and Item Builder */
function AccountPicker(opts) {
    /* opts: { accountSel, charSel, onCharSelect } */
    this.accountSel = document.querySelector(opts.accountSel);
    this.charSel    = document.querySelector(opts.charSel);
    this.onCharSelect = opts.onCharSelect || function(){};

    function csrfToken() {
        var c = document.cookie.split(';').map(function(s){ return s.trim(); })
            .filter(function(s){ return s.startsWith('csrf_token='); })[0];
        return c ? c.split('=')[1] : '';
    }

    function apiFetch(path, body) {
        return fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken() },
            body: JSON.stringify(body)
        }).then(function(r){ return r.json(); });
    }

    this.load = function() {
        var self = this;
        apiFetch('/api/accounts/list', {})
            .then(function(resp) {
                /* resp = [{error:""}, {0:{userid,username,...}, 1:{...}, ...}] */
                var usersDict = (Array.isArray(resp) && resp.length > 1) ? resp[1] : resp;
                var opt = document.createElement('option');
                opt.value = ''; opt.textContent = '— select account —';
                self.accountSel.appendChild(opt);
                Object.values(usersDict).forEach(function(a) {
                    if (!a || typeof a !== 'object' || !a.userid) return;
                    var o = document.createElement('option');
                    o.value = a.userid;
                    o.textContent = a.username + ' (' + a.userid + ')';
                    self.accountSel.appendChild(o);
                });
                self.accountSel.onchange = function() { self.loadChars(this.value); };
            });
    };

    this.loadChars = function(accountId) {
        var self = this;
        self.charSel.innerHTML = '<option value="">loading...</option>';
        self.charSel.disabled = true;
        if (!accountId) {
            self.charSel.innerHTML = '<option value="">— select character —</option>';
            return;
        }
        apiFetch('/api/accounts/chars', { id: parseInt(accountId, 10) })
            .then(function(resp) {
                /* resp = {0:{roleid,rolename,rolelevel,...}, 1:{...}, ...} */
                var chars = (resp && typeof resp === 'object' && !Array.isArray(resp)) ? Object.values(resp) : [];
                self.charSel.innerHTML = '';
                var validChars = chars.filter(function(r){ return r && r.roleid; });
                if (!validChars.length) {
                    var o = document.createElement('option');
                    o.value = ''; o.textContent = '— no characters —';
                    self.charSel.appendChild(o);
                    self.charSel.disabled = true;
                    return;
                }
                var blank = document.createElement('option');
                blank.value = ''; blank.textContent = '— select character —';
                self.charSel.appendChild(blank);
                validChars.forEach(function(r) {
                    var o = document.createElement('option');
                    o.value = r.roleid;
                    o.textContent = r.rolename + ' Lv' + r.rolelevel + ' (' + r.roleid + ')';
                    self.charSel.appendChild(o);
                });
                self.charSel.disabled = false;
                self.charSel.onchange = function() {
                    if (this.value) self.onCharSelect(parseInt(this.value, 10));
                };
            });
    };
}
