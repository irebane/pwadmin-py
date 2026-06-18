/* Shared account → character picker used by Roles and Item Builder */
function AccountPicker(opts) {
    /* opts: { accountSel, charSel, onCharSelect } */
    this.accountSel = document.querySelector(opts.accountSel);
    this.charSel    = document.querySelector(opts.charSel);
    this.onCharSelect = opts.onCharSelect || function(){};

    this.load = function() {
        var self = this;
        fetch('../php/accounts_get.php')
            .then(function(r){ return r.json(); })
            .then(function(accounts) {
                var opt = document.createElement('option');
                opt.value = ''; opt.textContent = '— select account —';
                self.accountSel.appendChild(opt);
                accounts.forEach(function(a) {
                    var o = document.createElement('option');
                    o.value = a.id; o.textContent = a.name + ' (' + a.id + ')';
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
        fetch('../php/roles.php?action=list&user-id=' + accountId)
            .then(function(r){ return r.json(); })
            .then(function(roles) {
                self.charSel.innerHTML = '';
                if (!roles || roles.length === 0) {
                    var o = document.createElement('option');
                    o.value = ''; o.textContent = '— no characters —';
                    self.charSel.appendChild(o);
                    self.charSel.disabled = true;
                    return;
                }
                var blank = document.createElement('option');
                blank.value = ''; blank.textContent = '— select character —';
                self.charSel.appendChild(blank);
                roles.forEach(function(r) {
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
