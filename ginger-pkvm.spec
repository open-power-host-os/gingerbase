%define mcp 8
%if 0%{?fedora} >= 15 || 0%{?rhel} >= 7 || 0%{?mcp} >= 8
%global with_systemd 1
%endif

%define frobisher_release 20
%define release .16
Name:		ginger
Version:	1.2.1
Release:	%{?frobisher_release}%{?release}%{?dist}
Summary:	Host management plugin for the Kimchi server
BuildRoot:	%{_topdir}/BUILD/%{name}-%{version}-%{release}
Group:		System Environment/Base
License:	LGPL/ASL2
BuildRequires:	gettext-devel >= 0.17
BuildRequires:	python-cheetah
Requires:	gettext >= 0.17
Requires:	kimchi = %{version}
Requires:	tuned
Requires:	libuser-python
Requires:	lm_sensors
Requires:	hddtemp

%ifarch ppc64 ppc
Requires:	powerpc-utils
Requires:	serviceable.event.provider
%endif

Obsoletes:	kimchi-ginger
Conflicts:	kimchi-ginger
Provides:	kimchi-ginger

%description
Ginger is a host management plugin to Kimchi, that provides an
intuitive web panel with common tools for configuring and operating
Linux systems. Kimchi is a web server application application to
manage KVM/Qemu virtual machines.


%prep
git clone git@git.linux.ibm.com:kimchi-ginger/ginger.git ./
git checkout --track remotes/origin/pkvm-2.1.1


%build
./autogen.sh --system
make

%install
rm -rf %{buildroot}
make DESTDIR=%{buildroot} install


%clean
rm -rf $RPM_BUILD_ROOT


%post
%if 0%{?with_systemd}
install -dm 0755 /usr/lib/systemd/system/kimchid.service.requires
ln -sf ../tuned.service /usr/lib/systemd/system/kimchid.service.requires
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
service kimchid restart
%endif


%postun
%if 0%{?with_systemd}
rm -f /usr/lib/systemd/system/kimchid.service.requires/tuned.service
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
service kimchid restart
%endif


%files
%attr(-,root,root)
%{python_sitelib}/kimchi/plugins/ginger/*.py*
%{python_sitelib}/kimchi/plugins/ginger/API.json
%{python_sitelib}/kimchi/plugins/ginger/controls/*.py*
%{python_sitelib}/kimchi/plugins/ginger/models/*.py*
%{_datadir}/kimchi/plugins/ginger/mo/*/LC_MESSAGES/ginger.mo
%{_datadir}/kimchi/plugins/ginger/ui/config/tab-ext.xml
%{_datadir}/kimchi/plugins/ginger/ui/css/base/images/*.gif
%{_datadir}/kimchi/plugins/ginger/ui/css/base/images/*.png
%{_datadir}/kimchi/plugins/ginger/ui/css/ginger.css
%{_datadir}/kimchi/plugins/ginger/ui/css/host-admin.css
%{_datadir}/kimchi/plugins/ginger/ui/js/host-admin.js
%{_datadir}/kimchi/plugins/ginger/ui/js/util.js
%{_datadir}/kimchi/plugins/ginger/ui/pages/help/en_US/host-admin.html
%{_datadir}/kimchi/plugins/ginger/ui/pages/help/pt_BR/host-admin.html
%{_datadir}/kimchi/plugins/ginger/ui/pages/help/zh_CN/host-admin.html
%{_datadir}/kimchi/plugins/ginger/ui/pages/host-admin.html.tmpl
%{_datadir}/kimchi/plugins/ginger/ui/pages/i18n.json.tmpl
%{_sysconfdir}/kimchi/plugins.d/ginger.conf


%changelog
* Thu Oct 2 2014 Rodrigo Trujillo <rodrigo.trujillo@linux.vnet.ibm.com> 1.2.1-20.16
- i18n support: Update translation files
- Add Ginger Help files - BZ#114095
- Changes Ginger PKVM spec according to Help feature and build 16

* Thu Sep 25 2014 Rodrigo Trujillo <rodrigo.trujillo@linux.vnet.ibm.com> 1.2.1-20.14
- host-admin.js: disabling OK button when processing - BZ#109251
- Add timeout check for configuration backup - BZ#109251
- Bugfix: Make buttons display properly when the text is long - BZ#116209
- Enhancement: Change the SEP status style from text to a status dot - BZ#116223
- Update Makefile.am to add autogen.sh in tarball.
- Deal with bad hdd sensor data - BZ#116332
- i18n support: Update translation files

* Thu Sep 11 2014 Paulo Vital <pvital@linux.vnet.ibm.com> 1.2.1-20.12
- i18n support: Add German translation - Bugzilla #115732
- i18n support: Add Spanish translation - Bugzilla #115732
- i18n support: Add French translation - Bugzilla #115732
- i18n support: Add Italian translation - Bugzilla #115732
- i18n support: Add Japanese translation - Bugzilla #115732
- i18n support: Add Korean translation - Bugzilla #115732
- i18n support: Add Russian translation - Bugzilla #115732
- i18n support: Add Traditional Chinese translation - Bugzilla #115732
- i18n support: Update Portuguese (Brazil) translation - Bugzilla #115732
- i18n support: Update Simplified Chinese translation - Bugzilla #115732
- Update spec file to PowerKVM 2.1.1 (20.12)

* Thu Sep 04 2014 Paulo Vital <pvital@linux.vnet.ibm.com> 1.2.1-20.11
- Bugfix Takes time to activate tuned profile in "Power Options" - Bugzilla #115184
- Update spec file to PowerKVM 2.1.1 (20.11)

* Thu Aug 21 2014 Rodrigo Trujillo <trujillo@linux.vnet.ibm.com> 1.2.1-20.9
- Bugfix: Change ginger's text for translation - BZ #115156
- IBM SEP bug fix: Update _get_subscribe info - BZ #115032
- Added missing packages requirements related to SEP and SENSORS features

* Fri Aug 15 2014 Rodrigo Trujillo <trujillo@linux.vnet.ibm.com> 1.2.1-20.8
- Update Ginger spec file to Power KVM 2.1.1 - Build 8
- Add sensors backend functionality - BZ #114422
- UI: Host sensors data visualization - BZ #114423
- UI: SEP(ESA) initial setup - BZ #114425
- IBM Serviceable Event Provider (SEP): Update build files - BZ #114424
- IBM Serviceable Event Provider (SEP): Backend support - BZ #114424
- IBM Serviceable Event Provider (SEP): Update configuration files - BZ #114424

* Wed Jul 23 2014 Rodrigo Trujillo <trujillo@linux.vnet.ibm.com> 1.2.1-20.4
- Added spec tags Obsoletes/Conflicts/Provides to update kimchi-ginger properly

* Tue Jul 15 2014 Paulo Vital  <pvital@linux.vnet.ibm.com> 1.2.1-20.3
- Created spec file to PowerKVM 2.1.1 (20.3)

* Wed Jul  2 2014 Paulo Vital <pvital@linux.vnet.ibm.com> 1.2.1
- Changed the package name from kimchi-ginger to ginger.

* Wed Apr 16 2014 Zhou Zheng Sheng <zhshzhou@linux.vnet.ibm.com> 1.2.0
- Initial release of Kimchi-ginger dedicated RPM package.
