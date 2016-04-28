# Create by zhihao.ding 2015/10/16

import os
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

user_data_file_context_dicts = {
    "syscloud_pass_config": "#cloud-config\n"\
            "ssh_pwauth: true\n"\
            "disable_root: 0\n"\
            "user: %s\n"\
            "password: %s\n"\
            "chpasswd:\n"\
            "    expire: false\n",
    "password_root": "#!/bin/bash\n"\
            "passwd root << EOF\n"\
            "%s\n"\
            "%s\n"\
            "EOF\n",
    "password_root_ubuntu_12": "#!/bin/bash\n"\
            "passwd root << EOF\n"\
            "%s\n"\
            "%s\n"\
            "EOF\n"\
            "useradd %s -m -r -s /bin/bash\n"\
            "passwd %s << EOF\n"\
            "%s\n"\
            "%s\n"\
            "EOF\n",
    "password_root_ubuntu": "#!/bin/bash\n"\
            "passwd root << EOF\n"\
            "%s\n"\
            "%s\n"\
            "EOF\n"\
            "passwd syscloud << EOF\n"\
            "%s\n"\
            "%s\n"\
            "EOF\n",
    "password_administrator": "rem cmd\n"\
            "net user Administrator %s\n",
    "data_volume_centos_rhel":"#!/bin/bash\n"\
            "fdisk /dev/vdb <<EOF\n"\
            "n\n"\
            "p\n"\
            "1\n"\
            "\n"\
            "\n"\
            "w\n"\
            "EOF\n"\
            "sleep 3\n"\
            "mkfs -t xfs /dev/vdb1\n"\
            "mkdir /data\n"\
            "mount /dev/vdb1 /data\n"\
            "echo '/dev/vdb1 /data xfs defaults 1 1' >>/etc/fstab\n",
    "data_volume_ubuntu_debian":"#!/bin/bash\n"\
            "fdisk /dev/vdb <<EOF\n"\
            "n\n"\
            "p\n"\
            "1\n"\
            "\n"\
            "\n"\
            "w\n"\
            "EOF\n"\
            "sleep 3\n"\
            "mkfs -t xfs /dev/vdb1\n"\
            "mkdir /data\n"\
            "mount /dev/vdb1 /data\n"\
            "echo '/dev/vdb1 /data xfs defaults 1 1' >>/etc/fstab\n",
    "data_volume_windows": "rem cmd\n"\
            "set script=attach_data_volume.txt\n"\
            "echo select disk 1 >  %script%\n"\
            "echo create partition primary >> %script%\n"\
            "echo active >> %script%\n"\
            "echo assign >> %script%\n"\
            "echo format quick >> %script%\n"\
            "diskpart /s %script%\n",
    "data_volume_linux_for_rebuild": "#!/bin/bash\n"\
            "mkdir /data\n"\
            "mount /dev/vdb1 /data\n"\
            "echo '/dev/vdb1 /data xfs defaults 1 1' >>/etc/fstab\n",
    "data_volume_windows_for_rebuild": "rem cmd\n"\
            "set script=attach_data_volume.txt\n"\
            "echo select disk 1 >  %script%\n"\
            "echo create partition primary >> %script%\n"\
            "echo active >> %script%\n"\
            "echo assign >> %script%\n"\
            "diskpart /s %script%\n",
    "last_step_for_windows": "rem cmd\n"\
            "set plugins_path=\"HKEY_LOCAL_MACHINE\\SOFTWARE\\Cloudbase Solutions\\Cloudbase-Init\\Plugins\" \n"\
            "set run_path=\"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\" \n"\
            "set python_bin=\"%ProgramFiles%\\Cloudbase Solutions\\Cloudbase-Init\\Python27\\python\" \n"\
            "set clear_userdata_bat=\"%WINDIR%\\clear_user_data.bat\" \n"\
            "set clear_userdata_py=\"%WINDIR%\\clear_user_data.py\" \n"\
            "echo reg add %plugins_path% /v UserDataPlugin /t REG_DWORD /d 0 /f > %clear_userdata_bat% \n"\
            "reg add %run_path% /v ClearUserData /t REG_SZ /d %clear_userdata_bat% /f \n"\
            "echo import urllib2 > %clear_userdata_py% \n"\
            "echo urllib2.urlopen(\"http://169.254.169.254/userdata/clear\") >> %clear_userdata_py% \n"\
            "%python_bin% %clear_userdata_py% \n"\
            "%clear_userdata_bat% \n",
    "last_step_for_centos_rhel": "#!/bin/bash\n"\
            "curl http://169.254.169.254/userdata/clear \n"\
            "sed -i 's/ssh_pwauth:.*/ssh_pwauth: 1/g' /etc/cloud/cloud.cfg \n"\
            "clear_filename=clear_sem_file.sh \n"\
            "abs_clear_file_path=/etc/init.d/$clear_filename \n"\
            "sem_files=/var/lib/cloud/instance/sem \n"\
            "script_files=/var/lib/cloud/instance/scripts \n"\
            "data_files=/var/lib/cloud/instance/*.* \n"\
            "echo \"#!/bin/bash\n\" > $abs_clear_file_path \n"\
            "echo \"# chkconfig: 2345 30 80\" >> $abs_clear_file_path \n"\
            "echo \"# description: clear sem files\n\" >> $abs_clear_file_path \n"\
            "echo \"main(){\" >> $abs_clear_file_path \n"\
            "echo \"for((i=1;i<=20;i++)); do\" >> $abs_clear_file_path \n"\
            "echo \"  sleep 20;\" >> $abs_clear_file_path \n"\
            "echo \"  if [ -d \"$sem_files\" ]; then\" >> $abs_clear_file_path \n"\
            "echo \"    sleep 10;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $sem_files;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $script_files;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $data_files;\" >> $abs_clear_file_path \n"\
            "echo \"  fi\" >> $abs_clear_file_path \n"\
            "echo \"done\" >> $abs_clear_file_path \n"\
            "echo \"}\" >> $abs_clear_file_path \n"\
            "echo \"main &\n\" >> $abs_clear_file_path \n"\
            "chmod +x $abs_clear_file_path \n"\
            "chkconfig --add $clear_filename \n"\
            "$abs_clear_file_path & \n",
    "last_step_for_ubuntu_debian": "#!/bin/bash\n"\
            "curl http://169.254.169.254/userdata/clear \n"\
            "clear_filename=clear_sem_file.sh \n"\
            "abs_clear_file_path=/etc/init.d/$clear_filename \n"\
            "sem_files=/var/lib/cloud/instance/sem \n"\
            "script_files=/var/lib/cloud/instance/scripts \n"\
            "data_files=/var/lib/cloud/instance/*.* \n"\
            "echo \"#!/bin/bash\n\" > $abs_clear_file_path \n"\
            "echo \"#\" >> $abs_clear_file_path \n"\
            "echo \"### BEGIN INIT INFO\" >> $abs_clear_file_path \n"\
            "echo \"# Provides: $clear_filename\" >> $abs_clear_file_path \n"\
            "echo \"# Required-Start: $local_fs\" >> $abs_clear_file_path \n"\
            "echo \"# Required-Stop: $local_fs\" >> $abs_clear_file_path \n"\
            "echo \"# X-Start-Before: \" >> $abs_clear_file_path \n"\
            "echo \"# Default-Start: S\" >> $abs_clear_file_path \n"\
            "echo \"# Default-Stop: \" >> $abs_clear_file_path \n"\
            "echo \"# Short-Description: clear sem files\" >> $abs_clear_file_path \n"\
            "echo \"# Description: \" >> $abs_clear_file_path \n"\
            "echo \"### END INIT INFO\" >> $abs_clear_file_path \n"\
            "echo \"#\n\" >> $abs_clear_file_path \n"\
            "echo \"main(){\" >> $abs_clear_file_path \n"\
            "echo \"for((i=1;i<=20;i++)); do\" >> $abs_clear_file_path \n"\
            "echo \"  sleep 20;\" >> $abs_clear_file_path \n"\
            "echo \"  if [ -d \"$sem_files\" ]; then\" >> $abs_clear_file_path \n"\
            "echo \"    sleep 10;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $sem_files;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $script_files;\" >> $abs_clear_file_path \n"\
            "echo \"    rm -rf $data_files;\" >> $abs_clear_file_path \n"\
            "echo \"  fi\" >> $abs_clear_file_path \n"\
            "echo \"done\" >> $abs_clear_file_path \n"\
            "echo \"}\" >> $abs_clear_file_path \n"\
            "echo \"main &\n\" >> $abs_clear_file_path \n"\
            "chmod +x $abs_clear_file_path \n"\
            "update-rc.d $clear_filename defaults \n"\
            "$abs_clear_file_path & \n",
}

class UserDataScriptHelper:
    base_dir = "/etc/openstack-dashboard/user_data"
    
    def __init__(self, image_name, is_create_data_volume=False, is_sync_set_root=False, is_rebuild=False):
        self._image_name = image_name
        self._is_create_data_volume = is_create_data_volume
        self._is_sync_set_root = is_sync_set_root
        self._is_rebuild = is_rebuild

    def _generate_password(self):
        symbolgroups = ('abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ',
                        '23456789', '.')
        length = 16

        r = random.SystemRandom()
        password = [r.choice(s) for s in symbolgroups]
        password = password[:length]
        length -= len(password)

        symbols = ''.join(symbolgroups)
        password.extend([r.choice(symbols) for _i in xrange(length)])

        return ''.join(password)

    def _create_file(self, file_path, filename):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        template = user_data_file_context_dicts.get(filename, '')

        try:
            with open(file_path, 'wb') as file:
                file.write(template)
        except Exception:
            pass

    def _get_file_context(self, filename):
        file_path = '/'.join((self.base_dir, filename))
        context = ''

        if filename not in user_data_file_context_dicts.keys():
            return context

        if not os.path.exists(file_path):
            try:
                self._create_file(file_path, filename)
            except Exception:
                pass

        try:
            with open(file_path, 'rb') as file:
                context = file.read()
        except Exception:
            context = user_data_file_context_dicts.get(filename, '')

        return context

    def _get_syscloud_pass_config_script(self, username, admin_pass):
        context = self._get_file_context('syscloud_pass_config')
        context = context % (username, admin_pass)
        return context

    def _get_last_step_for_centos_rhel_script(self):
        return self._get_file_context('last_step_for_centos_rhel')

    def _get_last_step_for_ubuntu_debian_script(self):
        return self._get_file_context('last_step_for_ubuntu_debian')

    def _get_last_step_for_windwos(self):
        return self._get_file_context("last_step_for_windows")

    def _get_password_root_script(self, password=None):
        context = self._get_file_context('password_root')
        password = password if (password and self._is_sync_set_root) else self._generate_password()
        context = context % (password, password)
        return context

    def _get_password_root_ubuntu_script(self, password=None):
        context = self._get_file_context('password_root_ubuntu')
        syscloud_password = password # must set user input password, in case user set username is 'syscloud'
        root_password = password if (password and self._is_sync_set_root) else self._generate_password()
        context = context % (root_password, root_password, syscloud_password, syscloud_password)
        return context

    def _get_password_root_ubuntu_12_script(self, username, password=None):
        context = self._get_file_context('password_root_ubuntu_12')
        syscloud_password = password # must set user input password, in case user set username is 'syscloud'
        root_password = password if (password and self._is_sync_set_root) else self._generate_password()
        context = context % (root_password, root_password, username, username, syscloud_password, syscloud_password)
        return context

    def _get_password_administrator_script(self, password=None):
        context = self._get_file_context('password_administrator')
        context = context % (password if (password and self._is_sync_set_root) else self._generate_password())
        return context

    def _get_data_volume_centos_rhel_script(self):
        return self._get_file_context('data_volume_centos_rhel')

    def _get_data_volume_ubuntu_debian_script(self):
        return self._get_file_context('data_volume_ubuntu_debian')

    def _get_data_volume_windows_script(self):
        return self._get_file_context('data_volume_windows')

    def _get_data_volume_linux_script_for_rebuild(self):
        return self._get_file_context("data_volume_linux_for_rebuild")

    def _get_data_volume_windows_script_for_rebuild(self):
        return self._get_file_context("data_volume_windows_for_rebuild")

    def _set_user_data_admin_pass(self, combined_msg, username=None, admin_pass=None):
        username = username if username else 'syscloud'
        admin_pass = admin_pass if admin_pass else self._generate_password()
        image_name = self._image_name
        if image_name.startswith('Ubuntu') and image_name.find('12.04') > 0:
            username = 'syscloud'
        admin_passwd_script = self._get_syscloud_pass_config_script(username, admin_pass)
        sub_msg = MIMEText(admin_passwd_script, 'cloud-config')
        combined_msg.attach(sub_msg)

    def _set_user_data_root_or_administrator_pass(self, combined_msg, username=None, password=None):
        if self._image_name is None:
            return
        image_name = self._image_name
        if image_name.startswith('Window'):
            password_script = self._get_password_administrator_script(password)
            sub_msg = MIMEText(password_script, 'x-shellscript')
            sub_msg.add_header('Content-Disposition', 'attachment; filename="administrator_pass.cmd"')
            combined_msg.attach(sub_msg)
        elif image_name.startswith('CentOS') or image_name.startswith('RHEL'):
            password_script = self._get_password_root_script(password)
            sub_msg = MIMEText(password_script, 'x-shellscript')
            combined_msg.attach(sub_msg)
        elif image_name.startswith('Ubuntu') or image_name.startswith('Debian'):
            if image_name.startswith('Ubuntu') and image_name.find('12.04') > 0:
                password_script = self._get_password_root_ubuntu_12_script(username, password)
            else:
                password_script = self._get_password_root_ubuntu_script(password)
            sub_msg = MIMEText(password_script, 'x-shellscript')
            combined_msg.attach(sub_msg)

    def _set_user_data_data_volume_preprocess(self, combined_msg):        
        if (self._image_name is None) or (not self._is_create_data_volume):
            return
        image_name = self._image_name
        if image_name.startswith('Window'):
            data_volume_script =  ''
            if self._is_rebuild:
                data_volume_script = self._get_data_volume_windows_script_for_rebuild()
            else:
                data_volume_script = self._get_data_volume_windows_script()
            #if image_name.find('2003') > 0:
            #    data_volume_script = data_volume_script % 1
            #else:
            #    data_volume_script = data_volume_script % 2
            sub_msg = MIMEText(data_volume_script, 'x-shellscript')
            sub_msg.add_header('Content-Disposition', 'attachment; filename="data_volume.cmd"')
            combined_msg.attach(sub_msg)
        elif image_name.startswith('CentOS') or image_name.startswith('RHEL'):
            data_volume_script = ''
            if self._is_rebuild:
                data_volume_script = self._get_data_volume_linux_script_for_rebuild()
            else:
                data_volume_script = self._get_data_volume_centos_rhel_script()
            sub_msg = MIMEText(data_volume_script, 'x-shellscript')
            combined_msg.attach(sub_msg)
        elif image_name.startswith('Ubuntu') or image_name.startswith('Debian'):
            data_volume_script = ''
            if self._is_rebuild:
                data_volume_script = self._get_data_volume_linux_script_for_rebuild()
            else:
                data_volume_script = self._get_data_volume_ubuntu_debian_script()
            sub_msg = MIMEText(data_volume_script, 'x-shellscript')
            combined_msg.attach(sub_msg)

    def _set_user_data_last_step(self, combined_msg):
        if self._image_name is None:
            return
        image_name = self._image_name
        if image_name.startswith('Window'):
            data_volume_script =  self._get_last_step_for_windwos()
            sub_msg = MIMEText(data_volume_script, 'x-shellscript')
            sub_msg.add_header('Content-Disposition', 'attachment; filename="clear_step.cmd"')
            combined_msg.attach(sub_msg)
        if image_name.startswith('CentOS') or image_name.startswith('RHEL'):
            terminal_cloudinit_script = self._get_last_step_for_centos_rhel_script()
            sub_msg = MIMEText(terminal_cloudinit_script, 'x-shellscript')
            combined_msg.attach(sub_msg)
        elif image_name.startswith('Ubuntu') or image_name.startswith('Debian'):
            terminal_cloudinit_script = self._get_last_step_for_ubuntu_debian_script()
            sub_msg = MIMEText(terminal_cloudinit_script, 'x-shellscript')
            combined_msg.attach(sub_msg)

    def get_user_data(self, username=None, admin_pass=None):
        combined_msg = MIMEMultipart()
        self._set_user_data_admin_pass(combined_msg, username, admin_pass)
        self._set_user_data_root_or_administrator_pass(combined_msg, username, admin_pass)
        self._set_user_data_data_volume_preprocess(combined_msg)
        self._set_user_data_last_step(combined_msg) # must put it last
        custom_script = '%s' % combined_msg
        return '\n'.join(custom_script.split('\n')[1:])

