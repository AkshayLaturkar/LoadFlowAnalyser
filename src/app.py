'''
Load FLow Analyser
Copyright (C) 2020 Akshay Arvind Laturkar   

Date Created : 25 March 2020 -- Version 1.0.0


This program is free software: you can redistribute it 
and/or modify it under the terms of the GNU General 
Public License as published by the Free Software 
Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be 
useful, but WITHOUT ANY WARRANTY; without even the 
implied warranty of MERCHANTABILITY or FITNESS FOR A 
PARTICULAR PURPOSE.  See the GNU General Public License 
for more details.

You should have received a copy of the GNU General Public 
License along with this program.  
If not, see <https://www.gnu.org/licenses/>.
'''

'''
File Version History
V1.0.0 : March 25, 2020 By Akshay Arvind Laturkar
V1.1.0 : March 28, 2020 By Akshay Arvind Laturkar
         Added New Feature for visualizing network power flows
V1.1.1 : March 28, 2020 By Akshay Arvind Laturkar
         Fixed a bug --> Removed development code from release
V1.1.2 : Marxh 29, 2020 By Akshay Arvind Laturkar
         Bug Fix, If redundant lines are present between buses, P was same
         Bug Fix, When Bus order is changed, YBus was wrongly referenced (No changes in this file)
'''


import sys; 
import gi;
gi.require_version('Gtk', '3.0');
from gi.repository import Gtk;
import numpy as np;
import pandas as pd;
from collections import Counter;
import loadflow as solver;
import signal;
import os;
import shutil;

class LoadFlowApp:

    '''
    App Initiation occurs here
    '''
    def __init__(self):

        try:
            # Fetch App Path
            self.path = os.getenv('LoadFlowPath');
            if self.path is None:
                self.path = '/'.join((os.getcwd().split('/'))[:-1]);

            # Fetch the GUI for the application
            self.builder = Gtk.Builder();
            self.builder.add_from_file(self.path+'/src/app.xml');
            self.builder.connect_signals(None);

            # Display the main application
            self.app = self.builder.get_object('window');
            self.app.set_icon_from_file(self.path+"/images/Help.png");
            self.app.show();

            # Attach App destroy event handler
            self.app.connect('destroy',self.on_app_destroy);

            # Store references to widgets
            self.widgets = {};
            self.widgets['window'] = self.app;
            self.widgets['menubar'] = self.builder.get_object('menu');
            self.widgets['status'] = self.builder.get_object('lblStatusMsg');
            self.widgets['networkfile'] = self.builder.get_object('fileNetwork');
            self.widgets['busfile'] = self.builder.get_object('fileBus');
            self.widgets['validatebutton'] = self.builder.get_object('btnValidate');
            self.widgets['beginloadflow'] = self.builder.get_object('btnBeginLoadFlow');
            self.widgets['viewresults'] = self.builder.get_object('btnViewResults');
            self.widgets['nonetworkfileimg'] = self.builder.get_object('imgNoNetworkFile');
            self.widgets['yesnetworkfileimg'] = self.builder.get_object('imgNetworkFile');
            self.widgets['nobusfileimg'] = self.builder.get_object('imgNoBusFile');
            self.widgets['yesbusfileimg'] = self.builder.get_object('imgBusFile');
            self.widgets['networkfilestatus'] = self.builder.get_object('lblNetworkFile');
            self.widgets['busfilestatus'] = self.builder.get_object('lblBusFile');
            self.widgets['removenetworkfile'] = self.builder.get_object('btnRemoveNetwork');
            self.widgets['removebusfile'] = self.builder.get_object('btnRemoveBus');
            self.widgets['infonetwork'] = self.builder.get_object('infonw');
            self.widgets['infobus'] = self.builder.get_object('infobus');
            self.widgets['novalidateimg'] = self.builder.get_object('imgNoValidated');
            self.widgets['yesvalidateimg'] = self.builder.get_object('imgYesValidated');
            self.widgets['validationstatus'] = self.builder.get_object('lblValidationStatus');
            self.widgets['config'] = self.builder.get_object('config');
            self.widgets['bus5'] = self.builder.get_object('bus5');
            self.widgets['bus14'] = self.builder.get_object('bus14');
            self.widgets['bus30'] = self.builder.get_object('bus30');
            self.widgets['bus118'] = self.builder.get_object('bus118');
            self.widgets['busfeed'] = self.builder.get_object('busfeed');
            self.widgets['linefeed'] = self.builder.get_object('linefeed');
            self.widgets['busresult'] = self.builder.get_object('busresult');
            self.widgets['lineflow'] = self.builder.get_object('lineflow');
            self.widgets['ybus'] = self.builder.get_object('ybus');
            self.widgets['data'] = self.builder.get_object('data');
            self.widgets['results'] = self.builder.get_object('results');
            self.widgets['about'] = self.builder.get_object('about');
            self.widgets['license'] = self.builder.get_object('license');
            self.widgets['bgimg'] = self.builder.get_object('imgBackground');
            self.widgets['imgnwinfo'] = self.builder.get_object('img1');
            self.widgets['imgbusinfo'] = self.builder.get_object('img2');
            self.widgets['visualize'] = self.builder.get_object('visualize');

            # App Variables
            self.nwdata = None;
            self.busdata = None;
            self.nwfilestatus = 0;
            self.busfilestatus = 0;
            self.buses = 0;
            self.YBus = None;
            self.iter = 0;
            self.OriginalBT = None;
            self.VLimit = True;
            self.QLimit = True;
            self.MaxIter = 20;
            self.rbusdata = None;
            self.rnwdata = None;

            # App Constants
            self.NW_HEADER = {'Line No':'int64','From Bus':'int64','To Bus':'int64',
                    'R':'float64','X':'float64','B/2':'float64','T':'float64'};
            self.BUS_HEADER = {'Bus No':'int64','Bus Type':'str','Pd':'float64','Qd':'float64',
                    'Pg':'float64','Qg':'float64','V':'float64','Shunt Feed':'float64','Qg (min)':'float64',
                    'Qg (max)':'float64','V (min)':'float64','V (max)':'float64'};
            self.NW_HEADER_DEFAULT = {'Line No':0,'From Bus':0,'To Bus':0,
                    'R':0.0,'X':0.0,'B/2':0.0,'T':1.0};
            self.BUS_HEADER_DEFAULT = {'Bus No':0,'Bus Type':'','Pd':0.0,'Qd':0.0,
                    'Pg':0.0,'Qg':0.0,'V':1.0,'Shunt Feed':0.0,'Qg (min)':0.0,
                    'Qg (max)':0.0,'V (min)':0.0,'V (max)':0.0};

            # Attach filters to file upload
            filter_file = Gtk.FileFilter();
            filter_file.set_name(".csv .xls .xlsx files");
            filter_file.add_mime_type("text/csv");
            #filter_file.add_mime_type("application/vnd.oasis.opendocument.spreadsheet");
            filter_file.add_mime_type("application/vnd.ms-excel");
            filter_file.add_mime_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            self.widgets['networkfile'].add_filter(filter_file);
            self.widgets['busfile'].add_filter(filter_file);

            # Attach event handlers to widgets
            self.widgets['networkfile'].connect('file-set',self.on_network_file_set);
            self.widgets['busfile'].connect('file-set',self.on_bus_file_set);
            self.widgets['validatebutton'].connect('clicked',self.on_validate_clicked);
            self.widgets['removenetworkfile'].connect('clicked',self.on_nwfile_remove);
            self.widgets['removebusfile'].connect('clicked',self.on_busfile_remove);
            self.widgets['beginloadflow'].connect('clicked',self.on_beginloadflow_clicked);
            self.widgets['viewresults'].connect('clicked',self.on_viewbusresults_clicked);
            self.widgets['config'].connect('activate',self.on_configure_activate);
            self.widgets['bus5'].connect('activate',self.on_bus5_activate);
            self.widgets['bus14'].connect('activate',self.on_bus14_activate);
            self.widgets['bus30'].connect('activate',self.on_bus30_activate);
            self.widgets['bus118'].connect('activate',self.on_bus118_activate);
            self.widgets['busfeed'].connect('activate',self.on_viewbusdata_activate);
            self.widgets['linefeed'].connect('activate',self.on_viewnwdata_activate);
            self.widgets['lineflow'].connect('activate',self.on_viewnwresults_activate);
            self.widgets['busresult'].connect('activate',self.on_viewbusresults_clicked);
            self.widgets['ybus'].connect('activate',self.on_ybus_activate);
            self.widgets['about'].connect('activate',self.on_view_about);
            self.widgets['license'].connect('activate',self.on_view_license);
            self.widgets['infonetwork'].connect('clicked',self.on_infonw_clicked);
            self.widgets['infobus'].connect('clicked',self.on_infobus_clicked);
            self.widgets['visualize'].connect('activate',self.DisplayGraph);

            # Set initial states of widgets
            self.widgets['status'].set_text('Ready');
            self.widgets['validatebutton'].set_sensitive(False);
            self.widgets['beginloadflow'].set_sensitive(False);
            self.widgets['viewresults'].set_sensitive(False);
            self.widgets['nonetworkfileimg'].show();
            self.widgets['yesnetworkfileimg'].hide();
            self.widgets['networkfilestatus'].set_text('No Line Feed Uploaded');
            self.widgets['nobusfileimg'].show();
            self.widgets['yesbusfileimg'].hide();
            self.widgets['busfilestatus'].set_text('No Bus Feed Uploaded');
            self.widgets['removenetworkfile'].set_sensitive(False);
            self.widgets['removebusfile'].set_sensitive(False);
            self.widgets['data'].set_sensitive(False);
            self.widgets['results'].set_sensitive(False);
            self.widgets['imgnwinfo'].set_from_file(self.path+"/images/Help.png");
            self.widgets['imgbusinfo'].set_from_file(self.path+"/images/Help.png");
            self.widgets['bgimg'].set_from_file(self.path+"/images/bg.png");
        except Exception as err:
            self.msglog(err);


    '''
    Function to destroy the app
    '''
    def on_app_destroy(self, widget):
        try:
            Gtk.main_quit();
        except Exception as err:
            self.msglog(err);

    '''
    Displays a popup to configure load flow on click of configure option in menubar
    '''
    def on_configure_activate(self, widget):
        try:
            dialog = None;

            # Create a popup
            dialog = Gtk.Dialog(title="Configure Load Flow Parameters",parent=self.app,modal=True,destroy_with_parent = True);
            dialog.set_resizable(False);
            self.widgets['configdialog'] = dialog;

            # Add a scroll bar to popup
            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(300,200);
            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            # Add UI Elements start
            label = Gtk.Label(xalign=0);
            label.set_text('Enable V limits');
            grid.attach(label,0,0,2,1);

            self.widgets['Vlimits'] = Gtk.Switch();
            self.widgets['Vlimits'].set_active(self.VLimit);
            grid.attach(self.widgets['Vlimits'],2,0,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Enable Qg limits');
            grid.attach(label,0,1,2,1);

            self.widgets['Qlimits'] = Gtk.Switch();
            self.widgets['Qlimits'].set_active(self.QLimit);
            grid.attach(self.widgets['Qlimits'],2,1,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Max NR iterations');
            grid.attach(label,0,2,2,1);

            adjustment = Gtk.Adjustment(lower=1,upper=100,page_increment=1,step_increment=1,value=self.MaxIter);
            self.widgets['maxIter'] = Gtk.SpinButton();
            self.widgets['maxIter'].set_adjustment(adjustment);
            grid.attach(self.widgets['maxIter'],2,2,3,1);

            button = Gtk.Button(label="OK");
            button.props.margin_left = 30;
            button.props.margin_right = 30;
            button.connect('clicked',self.on_config_set);
            grid.attach(button,1,3,2,1);
            # Add UI Elements end

            # Add contents to dialog and show the dialog
            box = dialog.get_content_area();
            scroll.add(grid);
            box.add(scroll);
            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    '''
    Set App constants from configuration popup
    '''
    def on_config_set(self, widget):
        try:
            # Set app constants
            self.MaxIter = int(self.widgets['maxIter'].get_text());
            self.VLimit = self.widgets['Vlimits'].get_active();
            self.QLimit = self.widgets['Qlimits'].get_active();
            self.widgets['configdialog'].destroy();
        except Exception as err:
            self.msglog(err);

    '''
    Load IEEE 5 Bus System
    '''
    def on_bus5_activate(self, widget):
        try:
            # Set filename in filechooser dialog
            busfile = self.path+'/examples/_5Bus/IEEE5_BusFeed.xlsx';
            nwfile = self.path + '/examples/_5Bus/IEEE5_LineFeed.xlsx';
            self.widgets['busfile'].set_filename(busfile);
            self.widgets['networkfile'].set_filename(nwfile);
            self.__uploadnetworkfile(nwfile);
            self.__uploadbusfile(busfile);
        except Exception as err:
            self.msglog(err);

    '''
    Load IEEE 14 Bus System
    '''
    def on_bus14_activate(self, widget):
        try:
            busfile = self.path + '/examples/_14Bus/IEEE14_BusFeed.xlsx';
            nwfile = self.path + '/examples/_14Bus/IEEE14_LineFeed.xlsx';
            self.widgets['busfile'].set_filename(busfile);
            self.widgets['networkfile'].set_filename(nwfile);
            self.__uploadnetworkfile(nwfile);
            self.__uploadbusfile(busfile);
        except Exception as err:
            self.msglog(err);

    '''
    Load IEEE 30 Bus System
    '''
    def on_bus30_activate(self, widget):
        try:
            busfile = self.path + '/examples/_30Bus/IEEE30_BusFeed.xlsx';
            nwfile = self.path + '/examples/_30Bus/IEEE30_LineFeed.xlsx';
            self.widgets['busfile'].set_filename(busfile);
            self.widgets['networkfile'].set_filename(nwfile);
            self.__uploadnetworkfile(nwfile);
            self.__uploadbusfile(busfile);
        except Exception as err:
            self.msglog(err);

    '''
    Load IEEE 118 Bus System
    '''
    def on_bus118_activate(self, widget):
        try:
            busfile = self.path + '/examples/_118Bus/IEEE118_BusFeed.xlsx';
            nwfile = self.path + '/examples/_118Bus/IEEE118_LineFeed.xlsx';
            self.widgets['busfile'].set_filename(busfile);
            self.widgets['networkfile'].set_filename(nwfile);
            self.__uploadnetworkfile(nwfile);
            self.__uploadbusfile(busfile);
        except Exception as err:
            self.msglog(err);



    '''
    Load Line Feed Data into app variable
    '''
    def __uploadnetworkfile(self,filename):
        try:
            ext = filename.split('.')[-1];
            if ext == 'ods':
                print("No Support for ODS Files");
                exit(1);
            elif ext == 'xls' or ext == 'xlsx':
                self.nwdata = pd.read_excel(filename,skip_blank_lines=True);
            elif ext == 'csv':
                self.nwdata = pd.read_csv(filename);
            else:
                print("Unknown File");
                exit(1);

            self.nwdata = self.nwdata.fillna(value=self.NW_HEADER_DEFAULT);

            self.widgets['nonetworkfileimg'].hide();
            self.widgets['yesnetworkfileimg'].show();
            self.widgets['networkfilestatus'].set_text('Line Feed Added');
            self.widgets['removenetworkfile'].set_sensitive(True);

            self.widgets['novalidateimg'].show();
            self.widgets['yesvalidateimg'].hide();
            self.widgets['validationstatus'].set_text('Data Not Validated');


            if(self.nwfilestatus == False):
                self.nwfilestatus = True;

            if(self.nwfilestatus and self.busfilestatus):
                self.widgets['validatebutton'].set_sensitive(True);
                self.widgets['beginloadflow'].set_sensitive(False);
                self.widgets['viewresults'].set_sensitive(False);
                self.widgets['data'].set_sensitive(False);
                self.widgets['results'].set_sensitive(False);
            else:
                self.widgets['validatebutton'].set_sensitive(False);
                self.widgets['beginloadflow'].set_sensitive(False);
                self.widgets['viewresults'].set_sensitive(False);
                self.widgets['data'].set_sensitive(False);
                self.widgets['results'].set_sensitive(False);
        except Exception as err:
            self.msglog(err);

    '''
    Load Bus Feed Data into app variable
    '''
    def __uploadbusfile(self,filename):
        try:
            ext = filename.split('.')[-1];
            if ext == 'ods':
                print("No Support for ODS Files");
                exit(1);
            elif ext == 'xls' or ext == 'xlsx':
                self.busdata = pd.read_excel(filename,skip_blank_lines=True);
            elif ext == 'csv':
                self.busdata = pd.read_csv(filename);
            else:
                print("Unknown File");
                exit(1);

            self.busdata = self.busdata.fillna(value=self.BUS_HEADER_DEFAULT);

            self.widgets['nobusfileimg'].hide();
            self.widgets['yesbusfileimg'].show();
            self.widgets['busfilestatus'].set_text('Bus Feed Added');
            self.widgets['removebusfile'].set_sensitive(True);

            self.widgets['novalidateimg'].show();
            self.widgets['yesvalidateimg'].hide();
            self.widgets['validationstatus'].set_text('Data Not Validated');

            if(self.busfilestatus == False):
                self.busfilestatus = True;

            if(self.nwfilestatus and self.busfilestatus):
                self.widgets['validatebutton'].set_sensitive(True);
                self.widgets['beginloadflow'].set_sensitive(False);
                self.widgets['viewresults'].set_sensitive(False);
                self.widgets['data'].set_sensitive(False);
                self.widgets['results'].set_sensitive(False);
            else:
                self.widgets['validatebutton'].set_sensitive(False);
                self.widgets['beginloadflow'].set_sensitive(False);
                self.widgets['viewresults'].set_sensitive(False);
                self.widgets['data'].set_sensitive(False);
                self.widgets['results'].set_sensitive(False);
        except Exception as err:
            self.msglog(err);

    '''
    Call the function which sets Line Feed
    '''
    def on_network_file_set(self, widget):
        try:
            filename = widget.get_filename();
            self.__uploadnetworkfile(filename);
        except Exception as err:
            self.msglog(err);

    '''
    Call the function which sets Bus Feed
    '''
    def on_bus_file_set(self, widget):
        try:
            filename = widget.get_filename();
            self.__uploadbusfile(filename);
        except Exception as err:
            self.msglog(err);

    '''
    Validation functions which validates data present in input files
    '''
    def on_validate_clicked(self, widget):

        try:
            # Set App Status
            self.widgets['status'].set_text('Validating Data...');

            # Check for valid data in Bus Feed
            bus = pd.DataFrame();
            columns = [col.strip().lower() for col in self.busdata.columns];
            for col,dtype in self.BUS_HEADER.items():
                if col.lower() in columns:
                    old_col = self.busdata.columns[columns.index(col.lower())];
                    self.busdata = self.busdata.rename(columns={old_col:col});
                    try:
                        self.busdata[col] = self.busdata[col].astype(dtype);
                        bus = pd.concat([bus,self.busdata[col]],axis=1);
                        if col == 'Bus No' or col == 'V' or col == 'V (min)' or col == 'V (max)':
                            if np.min(self.busdata[col]) < 0:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","'" + col + "' cannot be negative in Bus Feed File");
                                return;
                            if col == 'Bus No':
                                res = np.unique(list(Counter(self.busdata[col]).values()));
                                if(len(res) == 1 and res[0] == 1 and np.min(self.busdata[col]) == 1 
                                        and np.max(self.busdata[col]) == len(self.busdata[col])):
                                    self.buses = np.max(self.busdata[col]);
                                else:
                                    self.widgets['status'].set_text('Ready');
                                    self.msgdialog("Error","Bus No's are not in proper sequence");
                                    return;
                                if self.buses < 2:
                                    self.widgets['status'].set_text('Ready');
                                    self.msgdialog("Error","System should have atleast two buses");
                                    return;
                        if col == 'Bus Type':
                            if np.sum([0 if btype in ['Slack','PV','PQ'] else 1 for btype in Counter(self.busdata[col]).keys()]) !=0:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","Unknown bus type detected in Bus Feed");
                                return;
                            if Counter(self.busdata[col])['Slack'] != 1:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","More than 1 slack bus is not supported by the application.");
                                return;
                    except ValueError:
                        self.widgets['status'].set_text('Ready');
                        self.msgdialog("Error","Incorrect datatype for column '" + col + "' in the Bus Feed file");
                        return;
                else:
                    self.widgets['status'].set_text('Ready');
                    self.msgdialog("Error","Column '" + col + "' not found in the Bus Feed file");
                    return;
            self.busdata = bus.copy();

            # Check for valid data in Line Feed
            nw = pd.DataFrame();
            columns = [col.strip().lower() for col in self.nwdata.columns];
            for col,dtype in self.NW_HEADER.items():
                if col.lower() in columns:
                    old_col = self.nwdata.columns[columns.index(col.lower())];
                    self.nwdata = self.nwdata.rename(columns={old_col:col});
                    try:
                        self.nwdata[col] = self.nwdata[col].astype(dtype);
                        nw = pd.concat([nw,self.nwdata[col]],axis=1);
                        if col == 'Line No' or col == 'From Bus' or col == 'To Bus' or col == 'R' or col == 'X' or col == 'B/2' or col == 'T':
                            if np.min(self.nwdata[col]) < 0:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","'" + col + "' cannot be negative in Line Feed File");
                                return;
                        if col == 'From Bus':
                            if np.min(self.nwdata[col]) in list(self.busdata['Bus No']) and np.max(self.nwdata[col]) in list(self.busdata['Bus No']):
                                pass;
                            else:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","Invalid 'Bus No' in 'From Bus' of Line Feed");
                                return;
                        if col == 'To Bus':
                            if np.min(self.nwdata[col]) in list(self.busdata['Bus No']) and np.max(self.nwdata[col]) in list(self.busdata['Bus No']):
                                pass;
                            else:
                                self.widgets['status'].set_text('Ready');
                                self.msgdialog("Error","Invalid 'Bus No' in 'To Bus' of Line Feed");
                                return;
                    except ValueError:
                        self.widgets['status'].set_text('Ready');
                        self.msgdialog("Error","Incorrect datatype for column '" + col + "' in the Line Feed file");
                        return;
                else:
                    self.widgets['status'].set_text('Ready');
                    self.msgdialog("Error","Column '" + col + "' not found in the Line Feed file");
                    return;
            self.nwdata = nw.copy();

            self.YBus = np.zeros((self.buses,self.buses),dtype=complex);
            for idx in range(0,len(self.nwdata)):
                i = int(self.nwdata.iloc[idx]['From Bus']-1);
                j = int(self.nwdata.iloc[idx]['To Bus']-1);
                y = 1/(self.nwdata.iloc[idx]['R']+self.nwdata.iloc[idx]['X']*1j);
                b = self.nwdata.iloc[idx]['B/2']*1j;
                a = 1/self.nwdata.iloc[idx]['T'];
                self.YBus[i][i] += (a**2)*(y+b);
                self.YBus[i][j] -= a*y;
                self.YBus[j][i] -= a*y;
                self.YBus[j][j] += y+b;

            for idx in range(0,len(self.busdata)):
                i = int(self.busdata.iloc[idx]['Bus No']-1);
                b = self.busdata.iloc[idx]['Shunt Feed']*1j;
                self.YBus[i][i] += b;

            # Set Widget status
            self.widgets['nonetworkfileimg'].hide();
            self.widgets['yesnetworkfileimg'].show();
            self.widgets['networkfilestatus'].set_text('Line Feed Added');
            self.widgets['nobusfileimg'].hide();
            self.widgets['yesbusfileimg'].show();
            self.widgets['busfilestatus'].set_text('Bus Feed Added');
            self.widgets['removenetworkfile'].set_sensitive(True);
            self.widgets['removebusfile'].set_sensitive(True);
            self.widgets['novalidateimg'].hide();
            self.widgets['yesvalidateimg'].show();
            self.widgets['validationstatus'].set_text('Data Validated');
            self.msgdialog("Success","Both Line Feed and Bus Feed data has been validated.");
            self.widgets['beginloadflow'].set_sensitive(True);
            self.widgets['status'].set_text('Ready');
            self.widgets['data'].set_sensitive(True);
            self.widgets['results'].set_sensitive(False);
        except Exception as err:
            self.msglog(err);

    '''
    Call the load flow function
    '''
    def on_beginloadflow_clicked(self,widget):
        try:
            self.widgets['status'].set_text('Performing Load Flow');
            data = self.busdata;
            P = np.array(data['Pg']-data['Pd']).reshape((self.buses,1));
            Q = np.array(data['Qg']-data['Qd']).reshape((self.buses,1));
            Qmin = np.array(data['Qg (min)']).reshape((self.buses,1));
            Qmax = np.array(data['Qg (max)']).reshape((self.buses,1));
            Qd = np.array(data['Qd']).reshape((self.buses,1));
            Q = np.c_[Q,Qmin,Qmax,Qd];
            V = np.array(data['V']).reshape((self.buses,1));
            Vmin = np.array(data['V (min)']).reshape((self.buses,1));
            Vmax = np.array(data['V (max)']).reshape((self.buses,1));
            V = np.c_[V,Vmin,Vmax];
            BT = np.array(data['Bus Type']).reshape((self.buses,1));
            self.OriginalBT = BT.copy();
            Line = np.array(self.nwdata[['Line No','From Bus','To Bus','B/2','R','X']]).reshape((len(self.nwdata),6));

            # Added BNo data as part of Bug Fix -V1.1.2
            BNo = np.array(data['Bus No']).reshape((self.buses,1));

            # Call Load Flow Solver
            lf = solver.LoadFlow(self.buses,P,Q,V,BT,self.YBus,self.MaxIter,self.VLimit,self.QLimit,Line,BNo);

            [rIter,rBT,rP,rQ,rV,rD,Pavg,Qavg,Ploss,Qloss] = lf.Solve();
            self.rbusdata = self.busdata.copy();
            self.rnwdata = self.nwdata.copy();
            self.rbusdata['Pg'] = rP + np.array(self.rbusdata['Pd']).reshape((self.buses,1));
            self.rbusdata['Qg'] = rQ[:,0].reshape((self.buses,1)) + Qd;
            self.rbusdata['V'] = rV[:,0];
            self.rbusdata['D'] = rD[:,0]*180/np.pi;
            self.rbusdata['Bus Type'] = rBT[:,0];
            self.rnwdata['Pavg'] = Pavg;
            self.rnwdata['Ploss'] = Ploss;
            self.rnwdata['Qavg'] = Qavg;
            self.rnwdata['Qloss'] = Qloss;
            self.iter = rIter;
            self.msgdialog("Success","Load Flow Completed. Iterations taken : "+str(rIter));
            self.widgets['viewresults'].set_sensitive(True);
            self.widgets['status'].set_text('Ready');
            self.widgets['results'].set_sensitive(True);
        except Exception as err:
            self.msglog(err);

    '''
    Remove Line Feed from filechooser dialog
    '''
    def on_nwfile_remove(self, widget):
        try:
            self.widgets['networkfile'].unselect_all();
            self.widgets['nonetworkfileimg'].show();
            self.widgets['yesnetworkfileimg'].hide();
            self.widgets['networkfilestatus'].set_text('No Line Feed Added');
            self.widgets['novalidateimg'].show();
            self.widgets['yesvalidateimg'].hide();
            self.widgets['validationstatus'].set_text('Data Not Validated');
            self.nwfilestatus = False;
            self.nwdata = None;
            self.widgets['validatebutton'].set_sensitive(False);
            self.widgets['beginloadflow'].set_sensitive(False);
            self.widgets['viewresults'].set_sensitive(False);
            self.widgets['data'].set_sensitive(False);
            self.widgets['results'].set_sensitive(False);
        except Exception as err:
            self.msglog(err);

    '''
    Remove Bus Fed from filechooser dialog
    '''
    def on_busfile_remove(self, widget):
        try:
            self.widgets['busfile'].unselect_all();
            self.widgets['nobusfileimg'].show();
            self.widgets['yesbusfileimg'].hide();
            self.widgets['busfilestatus'].set_text('No Bus Feed Added');
            self.widgets['novalidateimg'].show();
            self.widgets['yesvalidateimg'].hide();
            self.widgets['validationstatus'].set_text('Data Not Validated');
            self.busfilestatus = False;
            self.busdata = None;
            self.widgets['validatebutton'].set_sensitive(False);
            self.widgets['beginloadflow'].set_sensitive(False);
            self.widgets['viewresults'].set_sensitive(False);
            self.widgets['data'].set_sensitive(False);
            self.widgets['results'].set_sensitive(False);
        except Exception as err:
            self.msglog(err);


    def on_viewbusdata_activate(self,widget):
        self.__DisplayBusData('Data');

    def on_viewbusresults_clicked(self,widget):
        self.__DisplayBusData('Results');

    def on_viewnwdata_activate(self,widget):
        self.__DisplayLineData('Data');

    def on_viewnwresults_activate(self,widget):
        self.__DisplayLineData('Results');

    def on_ybus_activate(self,widget):
        self.__DisplayYBus();

    '''
    Display Bus Data for Results as well as Input Data
    mode = Results => Final Output Data
    mode = Data => Input Data
    '''
    def __DisplayBusData(self,mode):
        try:
            dialog = None;
            if mode == 'Data':
                dialog = Gtk.Dialog(title="Bus Feed",parent=self.app,modal=True,destroy_with_parent = True);
                height = (self.buses+2)*30;
                shift = 0;
                data = self.busdata;
            else:
                dialog = Gtk.Dialog(title="BUS V,Q Profile",parent=self.app,modal=True,destroy_with_parent = True);
                height = (self.buses+4)*30;
                shift = 1;
                data = self.rbusdata;

            dialog.set_resizable(False);
            
            if height > 500:
                height = 500;

            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(750, height);
            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            offset = 3;

            titleBNo = Gtk.Label();
            titleBNo.set_markup('<b>Bus No</b>');
            grid.attach(titleBNo,0,offset,1,1);

            titleBT = Gtk.Label();
            titleBT.set_markup('<b>Bus Type</b>');
            grid.attach(titleBT,1,offset,1,1);

            titleV = Gtk.Label();
            titleV.set_markup('<b>V (pu)</b>');
            grid.attach(titleV,2,offset,1,1);

            if mode == 'Results':
                titleD = Gtk.Label();
                titleD.set_markup('<b>D (deg)</b>');
                grid.attach(titleD,3,offset,1,1);

            titlePg = Gtk.Label();
            titlePg.set_markup('<b>Pg (pu)</b>');
            grid.attach(titlePg,3+shift,offset,1,1);

            titlePd = Gtk.Label();
            titlePd.set_markup('<b>Pd (pu)</b>');
            grid.attach(titlePd,4+shift,offset,1,1);

            titleQg = Gtk.Label();
            titleQg.set_markup('<b>Qg (pu)</b>');
            grid.attach(titleQg,5+shift,offset,1,1);

            titleQd = Gtk.Label();
            titleQd.set_markup('<b>Qd (pu)</b>');
            grid.attach(titleQd,6+shift,offset,1,1);

            if mode == 'Data':
                titleQmin = Gtk.Label();
                titleQmin.set_markup('<b>Qg (min)</b>');
                grid.attach(titleQmin,7+shift,offset,1,1);

                titleQmax = Gtk.Label();
                titleQmax.set_markup('<b>Qg (max)</b>');
                grid.attach(titleQmax,8+shift,offset,1,1);

                titleVmin = Gtk.Label();
                titleVmin.set_markup('<b>V (min)</b>');
                grid.attach(titleVmin,9+shift,offset,1,1);

                titleVmax = Gtk.Label();
                titleVmax.set_markup('<b>V (max)</b>');
                grid.attach(titleVmax,10+shift,offset,1,1);

            for i in range(0,self.buses):

                label = Gtk.Label();
                label.set_text(str(data['Bus No'][i]));
                grid.attach(label,0,i+1+offset,1,1);

                label = Gtk.Label();
                val = str(data['Bus Type'][i]);
                if mode == 'Results' and val != str(self.OriginalBT[i][0]):
                    label.set_markup('<span foreground="red">'+val+'</span>');
                else:
                    label.set_text(val);
                grid.attach(label,1,i+1+offset,1,1);

                label = Gtk.Label();
                Vval = data['V'][i];
                Vmin = data['V (min)'][i];
                Vmax = data['V (max)'][i];
                if ((Vval-Vmin)<-1e-6 or (Vval-Vmax)>1e-6) and abs(Vmax-Vmin)>1e-3 and mode == 'Results':
                    label.set_markup('<span foreground="red">'+"{0:8.5f}".format(Vval)+'</span>');
                else:
                    label.set_text("{0:8.5f}".format(Vval));
                grid.attach(label,2,i+1+offset,1,1);

                if mode == 'Results':
                    label = Gtk.Label();
                    label.set_text("{0:8.4f}".format(data['D'][i]));
                    grid.attach(label,3,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['Pg'][i]));
                grid.attach(label,3+shift,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['Pd'][i]));
                grid.attach(label,4+shift,i+1+offset,1,1);

                label = Gtk.Label();
                Qval = data['Qg'][i];
                Qmin = data['Qg (min)'][i];
                Qmax = data['Qg (max)'][i];
                if ((Qval-Qmin)<-1e-6 or (Qval-Qmax)>1e-6) and abs(Qmax-Qmin)>1e-3 and mode =='Results':
                    label.set_markup('<span foreground="red">'+"{0:8.5f}".format(Qval)+'</span>');
                else:
                    label.set_text("{0:8.5f}".format(Qval));
                grid.attach(label,5+shift,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['Qd'][i]));
                grid.attach(label,6+shift,i+1+offset,1,1);

                if mode == 'Data':

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(Qmin));
                    grid.attach(label,7+shift,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(Qmax));
                    grid.attach(label,8+shift,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(Vmin));
                    grid.attach(label,9+shift,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(Vmax));
                    grid.attach(label,10+shift,i+1+offset,1,1);


            box = dialog.get_content_area();
            scroll.add(grid);

            box.add(scroll);

            if mode == 'Results':
                
                button = Gtk.Button(label='Download as CSV');
                button.connect('clicked',self.on_savebusdata);
                button.props.margin_left = 240;
                button.props.margin_right = 240;
                button.props.margin_top = 20;
                button.props.margin_bottom = 20;
                box.add(button);
                self.tempdata = data;


            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    def on_savebusdata(self,widget):
        self.saveresultsfiledialog(None,self.tempdata);

    '''
    Display Line data for both Input and Results
    mode = Results => Final Output Data
    mode = Data => Input Data
    '''
    def __DisplayLineData(self,mode):
        try:
            dialog = None;
            if mode == 'Data':
                dialog = Gtk.Dialog(title="Line Feed",parent=self.app,modal=True,destroy_with_parent = True);
                data = self.nwdata;
                if data is not None:
                    height = (len(data)+2)*30;
                else:
                    height = 60;
                width = 650;
            else:
                dialog = Gtk.Dialog(title="Line Power Flows",parent=self.app,modal=True,destroy_with_parent = True);
                data = self.rnwdata;
                if data is not None:
                    height = (len(data)+6)*30;
                else:
                    height = 60;
                width = 750

            dialog.set_resizable(False);

            if height > 500:
                height = 500;

            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(width, height);
            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            offset = 3;

            label = Gtk.Label();
            label.set_markup('<b>Line No</b>');
            grid.attach(label,0,offset,1,1);

            label = Gtk.Label();
            label.set_markup('<b>From Bus</b>');
            grid.attach(label,1,offset,1,1);

            label = Gtk.Label();
            label.set_markup('<b>To Bus</b>');
            grid.attach(label,2,offset,1,1);

            label = Gtk.Label();
            label.set_markup('<b>R (pu)</b>');
            grid.attach(label,3,offset,1,1);

            label = Gtk.Label();
            label.set_markup('<b>X (pu)</b>');
            grid.attach(label,4,offset,1,1);

            label = Gtk.Label();
            label.set_markup('<b>B/2 (pu)</b>');
            grid.attach(label,5,offset,1,1);

            if mode == 'Data':
                label = Gtk.Label();
                label.set_markup('<b>T</b>');
                grid.attach(label,6,offset,1,1);
            else:
                label = Gtk.Label();
                label.set_markup('<b>Avg P (pu)</b>');
                grid.attach(label,6,offset,1,1);

                label = Gtk.Label();
                label.set_markup('<b>P loss (pu)</b>');
                grid.attach(label,7,offset,1,1);

                label = Gtk.Label();
                label.set_markup('<b>Avg Q (pu)</b>');
                grid.attach(label,8,offset,1,1);

                label = Gtk.Label();
                label.set_markup('<b>Q consumed (pu)</b>');
                grid.attach(label,9,offset,1,1);

            if data is not None:
                n = len(data);
            else:
                n = 0;

            for i in range(0,n):
                
                label = Gtk.Label();
                label.set_text(str(data['Line No'][i]));
                grid.attach(label,0,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text(str(data['From Bus'][i]));
                grid.attach(label,1,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text(str(data['To Bus'][i]));
                grid.attach(label,2,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['R'][i]));
                grid.attach(label,3,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['X'][i]));
                grid.attach(label,4,i+1+offset,1,1);

                label = Gtk.Label();
                label.set_text("{0:8.5f}".format(data['B/2'][i]));
                grid.attach(label,5,i+1+offset,1,1);

                if mode == 'Data':

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(data['T'][i]));
                    grid.attach(label,6,i+1+offset,1,1);
                
                if mode == 'Results':

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(data['Pavg'][i]));
                    grid.attach(label,6,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(data['Ploss'][i]));
                    grid.attach(label,7,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(data['Qavg'][i]));
                    grid.attach(label,8,i+1+offset,1,1);

                    label = Gtk.Label();
                    label.set_text("{0:8.5f}".format(data['Qloss'][i]));
                    grid.attach(label,9,i+1+offset,1,1);


            if mode == 'Results':
                label = Gtk.Label(xalign=0);
                label.set_text("Total line losses : {0:8.5f}".format(np.sum(data['Ploss'])));
                grid.attach(label,0,i+2+offset,3,1);

                label = Gtk.Label(xalign=0);
                label.set_text("Total Q consumed by lines : {0:8.5f}".format(np.sum(data['Qloss'])));
                grid.attach(label,0,i+3+offset,3,1);


            box = dialog.get_content_area();
            scroll.add(grid);
            box.add(scroll);

            if mode == 'Results':
                button = Gtk.Button(label='Download as CSV');
                button.connect('clicked',self.on_savelinedata);
                button.props.margin_left = 240;
                button.props.margin_right = 240;
                button.props.margin_top = 20;
                button.props.margin_bottom = 20;
                self.tempdata = data;
                box.add(button);

            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    def on_savelinedata(self,widget):
        self.saveresultsfiledialog(None,self.tempdata);

    '''
    Display YBus Matrix
    '''
    def __DisplayYBus(self):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title="Y Bus",parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            height = 30*(self.buses+2);
            width = 175*self.buses;

            if height > 500:
                height = 500;

            if width > 750:
                width = 750;

            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(width, height);
            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            for i in range(0,self.buses):
                label = Gtk.Label();
                label.set_markup('<b>'+str(i+1)+'</b>');
                grid.attach(label,0,i+1,1,1);

                label = Gtk.Label();
                label.set_markup('<b>'+str(i+1)+'</b>');
                grid.attach(label,i+1,0,1,1);

            for i in range(0,self.buses):
                for j in range(0,self.buses):
                    label = Gtk.Label();
                    re = self.YBus[i][j].real;
                    im = self.YBus[i][j].imag;
                    label.set_text('{0:7.3f} {1} {2:.3f}i'.format(re, '-' if im < 0 else '+', abs(im)));
                    grid.attach(label,j+1,i+1,1,1);

            box = dialog.get_content_area();
            scroll.add(grid);
            box.add(scroll);
            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);


    '''
    Display popup for About Menu
    '''
    def on_view_about(self,widgets):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title="About",parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(255,240);
            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            label = Gtk.Label();
            label.set_markup('<span foreground="green"><b>Load Flow Analyser</b></span>');
            grid.attach(label,0,0,1,1);

            label = Gtk.Label();
            label.set_markup('<b>Author</b>');
            grid.attach(label,0,1,1,1);

            label = Gtk.Label();
            label.set_markup('Akshay Arvind Laturkar');
            grid.attach(label,0,2,1,1);

            label = Gtk.Label();
            label.set_markup('Current App Version : 1.1.2');
            grid.attach(label,0,3,1,1);

            label = Gtk.Label();
            label.set_markup('Date Published : 29 March 2020');
            grid.attach(label,0,4,1,1);

            label = Gtk.Label();
            label.set_markup('License : GPL 3');
            grid.attach(label,0,5,1,1);

            box = dialog.get_content_area();
            scroll.add(grid);
            box.add(scroll);
            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    '''
    Display application license in a popup
    '''
    def on_view_license(self,widget):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title="License",parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True);
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC);

            dialog.set_default_size(550,300);

            buffer1 = Gtk.TextBuffer();
            
            f = open(self.path+'/license.txt','r');
            content = f.read();
            buffer1.set_text(content);

            textview = Gtk.TextView(buffer=buffer1);
            textview.set_wrap_mode(Gtk.WrapMode.WORD);
            textview.set_monospace(True);
            textview.set_editable(False);
            textview.set_cursor_visible(False);

            box = dialog.get_content_area();
            scroll.add(textview);
            box.add(scroll);
            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    '''
    File Dialog to save Template files
    '''
    def savefiledialog(self,source,data=None):
        try:
            dialog = None;
            dialog = Gtk.FileChooserDialog(title="Save template", parent=self.app,action=Gtk.FileChooserAction.SAVE);
            dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL);
            dialog.add_button(Gtk.STOCK_OK,Gtk.ResponseType.OK);

            filter_file = Gtk.FileFilter();
            filter_file.set_name(".xlsx files");
            filter_file.add_mime_type("application/vnd.ms-excel");
            filter_file.add_mime_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
            dialog.add_filter(filter_file);

            dialog.set_filename(os.getenv('HOME')+'/tempfile.xlsx');

            response = dialog.run();

            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename();
                if '.xlsx' in filename and filename[-5:] == '.xlsx':
                    self.copyfile(source,filename);
                else:
                    self.copyfile(source,filename+'.xlsx');
                dialog.destroy();
            elif response == Gtk.ResponseType.CANCEL:
                dialog.destroy();
            dialog.destroy();
        except Exception as err:
            self.msglog(err,quit=False,msg="Error occured while saving file",parent=dialog);
            dialog.destroy();

    '''
    File Dialog to save Resuts Data
    '''
    def saveresultsfiledialog(self,source,data=None):
        try:
            dialog = None;
            dialog = Gtk.FileChooserDialog(title="Save File", parent=self.app,action=Gtk.FileChooserAction.SAVE);
            dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL);
            dialog.add_button(Gtk.STOCK_OK,Gtk.ResponseType.OK);

            filter_file = Gtk.FileFilter();
            filter_file.set_name(".csv files");
            filter_file.add_mime_type("text/csv");
            dialog.add_filter(filter_file);

            dialog.set_filename(os.getenv('HOME')+'/tempresults.csv');

            response = dialog.run();

            if response == Gtk.ResponseType.OK:
                filename = dialog.get_filename();
                if '.csv' in filename and filename[-4:] == '.csv':
                    self.savefile(data,filename);
                else:
                    self.savefile(data,filename+'.csv');
                dialog.destroy();
            elif response == Gtk.ResponseType.CANCEL:
                dialog.destroy();
            dialog.destroy();
        except PermissionError as err:
            self.msglog(err, quit=False, msg='Permission denied', parent=dialog);
            dialog.destroy();
        except Exception as err:
            self.msglog(err);

    '''
    Help popup for Bus Feed
    '''
    def on_infobus_clicked(self, widget):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title='Help',parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            self.widgets['temp'] = dialog;

            label = Gtk.Label();
            label.set_text('Bus Feed needs to have following format. Use the template file provided below to upload data');
            label.set_line_wrap(True);
            label.set_max_width_chars(50);
            label.set_justify(Gtk.Justification.CENTER);
            dialog.vbox.add(label);

            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            label = Gtk.Label(xalign=0);
            label.set_text('Column 1 : Bus No (int)');
            label.props.margin_top = 20;
            grid.attach(label,0,0,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 2 : Bus Type (string)');
            label.props.margin_top = 20;
            grid.attach(label,1,0,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 3 : Pd (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,1,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 4 : Qd (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,1,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 5 : Pg (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,2,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 6 : Qg (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,2,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 7 : V (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,3,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 8 : Shunt Feed (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,3,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 9 : Qg (min) (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,4,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 10 : Qg (max) (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,4,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 11 : V (min) (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,5,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 12 : V (max) (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,5,1,1);

            dialog.vbox.add(grid);

            button = Gtk.Button(label="Download Bus Feed Template");
            button.connect('clicked',self.on_infobus_btn_clicked);
            button.props.margin_left = 80;
            button.props.margin_right = 80;
            button.props.margin_top = 20;
            dialog.vbox.add(button);

            dialog.vbox.props.margin_top = 20;
            dialog.vbox.props.margin_bottom = 20;
            dialog.vbox.props.margin_left = 20;
            dialog.vbox.props.margin_right = 20;

            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    def copyfile(self,source,dest):
        print(source);
        print(dest);
        shutil.copyfile(source,dest);

    def savefile(self,data,dest):
        data.to_csv(dest,index=False);

    '''
    Bus Feed Template Save Button click Handler
    '''
    def on_infobus_btn_clicked(self, widget):
        try:
            source = self.path+'/examples/template/Template_BusFeed.xlsx';
            self.savefiledialog(source);
            self.widgets['temp'].destroy();
        except Exception as err:
            self.msglog(err);

    '''
    Help popup for Bus Feed
    '''
    def on_infonw_clicked(self, widget):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title='Help',parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            self.widgets['temp'] = dialog;

            label = Gtk.Label();
            label.set_text('Line Feed needs to have following format. Use the template file provided below to upload data');
            label.set_line_wrap(True);
            label.set_max_width_chars(50);
            label.set_justify(Gtk.Justification.CENTER);
            dialog.vbox.add(label);

            grid = Gtk.Grid(column_spacing=30,row_spacing=10);
            grid.props.margin_left = 20;
            grid.props.margin_top = 20;
            grid.props.margin_right = 20;
            grid.props.margin_bottom = 20;

            label = Gtk.Label(xalign=0);
            label.set_text('Column 1 : Line No (int)');
            label.props.margin_top = 20;
            grid.attach(label,0,0,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 2 : From Bus (int)');
            label.props.margin_top = 20;
            grid.attach(label,1,0,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 3 : To Bus (int)');
            label.props.margin_top = 20;
            grid.attach(label,0,1,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 4 : R (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,1,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 5 : X (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,2,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 6 : B/2 (float)');
            label.props.margin_top = 20;
            grid.attach(label,1,2,1,1);

            label = Gtk.Label(xalign=0);
            label.set_text('Column 7 : T (float)');
            label.props.margin_top = 20;
            grid.attach(label,0,3,1,1);

            dialog.vbox.add(grid);

            button = Gtk.Button(label="Download Line Feed Template");
            button.connect('clicked',self.on_infonw_btn_clicked);
            button.props.margin_left = 80;
            button.props.margin_right = 80;
            button.props.margin_top = 20;
            dialog.vbox.add(button);

            dialog.vbox.props.margin_top = 20;
            dialog.vbox.props.margin_bottom = 20;
            dialog.vbox.props.margin_left = 20;
            dialog.vbox.props.margin_right = 20;

            dialog.show_all();
        except Exception as err:
            self.msglog(err,parent=dialog);

    '''
    Line Feed Template Save Button click Handler
    '''
    def on_infonw_btn_clicked(self, widget):
        try:
            source = self.path+'/examples/template/Template_LineFeed.xlsx';
            self.savefiledialog(source);
            self.widgets['temp'].destroy();
        except Exception as err:
            self.msglog(err);


    '''
    Dialog to show validation messages
    '''
    def msgdialog(self,msgtype,msg):
        try:
            dialog = None;
            dialog = Gtk.Dialog(title=msgtype,parent=self.app,modal=True,destroy_with_parent = True);

            dialog.set_resizable(False);

            label = Gtk.Label();
            label.set_text(msg);
            label.set_line_wrap(True);
            label.set_max_width_chars(50);
            label.set_justify(Gtk.Justification.CENTER);
            dialog.vbox.add(label);

            dialog.vbox.props.margin_top = 20;
            dialog.vbox.props.margin_bottom = 20;
            dialog.vbox.props.margin_left = 20;
            dialog.vbox.props.margin_right = 20;

            button = Gtk.Button(label='OK');
            button.props.margin_top = 20;
            button.props.margin_left = 100;
            button.props.margin_right = 100;
            self.msgdialogwidget = dialog;
            button.connect('clicked',self.msgdialogOK_clicked);
            dialog.vbox.add(button);

            dialog.show_all();
        except Exception as err:
            self.msglog(err, parent=dialog);

    '''
    OK click Handler for validation messages
    '''
    def msgdialogOK_clicked(self,widget):
        try:
            self.msgdialogwidget.destroy();
        except Exception as err:
            self.msglog(Exception, err);

    '''
    Main Application Loop
    '''
    def main(self):
        try:
            Gtk.main();
        except Exception as err:
            self.msglog(err);

    '''
    Draw network as graph
    Added New feature on March 28, 2020 - V 1.1.0
    '''
    def DisplayGraph(self,widget):

        from graphviz import Digraph;
        s = Digraph(engine='dot',node_attr={'style': 'filled'});
        s.attr('node', shape='circle', fixedsize='true',width='1.5');
        s.attr(rankdir='LR');

        for i in range(0,len(self.rbusdata)):
            busno = str(self.rbusdata['Bus No'][i])
            p='\n'+'Pg = '+"{0:.3f}".format(self.rbusdata['Pg'][i])+"\n"+"Pd = "+"{0:.3f}".format(self.rbusdata['Pd'][i]);
            if self.busdata['Bus Type'][i] == 'PQ':
                if abs(self.rbusdata['Pd'][i]) < 1e-4:
                    color = '#BEBEBE';
                else:
                    color = '#FF7900';
            elif self.busdata['Bus Type'][i] == 'Slack':
                color = '#E0B0FF';
            else:
                if abs(self.rbusdata['Pg'][i]) < 1e-4:
                    color = '#71BC78';
                else:
                    color = '#0080FF';
            s.node(busno,label='Bus : '+busno+p,fillcolor=color);

        for i in range(0,len(self.rnwdata)):
            frombus = str(self.rnwdata['From Bus'][i]);
            tobus = str(self.rnwdata['To Bus'][i]);
            p = "{0:.3f}".format(self.rnwdata['Pavg'][i]);
            if float(p) > 0:
                s.edge(frombus,tobus,label=p);
            else:
                s.edge(tobus,frombus,label=str(abs(float(p))));

        with s.subgraph(name='Details') as b:
            s.attr('node', shape='rectangle', fixedsize='true',width='3');
            b.node('Dummy',label='Dummy Bus',fillcolor='#BEBEBE');
            b.node('PQ',label='Load PQ Bus',fillcolor='#FF7900');
            b.node('V Bus',label='Voltage Controlled Bus',fillcolor='#71BC78');
            b.node('PV',label='Generator PV Bus',fillcolor='#0080FF');
            b.node('Slack',label='Generator Slack Bus',fillcolor='#E0B0FF');

        import tempfile;
        s.view(tempfile.mktemp('.gv'));

    '''
    Error Message dialog window
    '''
    def msglog(self,err,quit=True,msg=None,parent=None):
        if parent is None:
            dialog = Gtk.Dialog(title='Error',parent=self.app,modal=True,destroy_with_parent=True);
        else:
            dialog = Gtk.Dialog(title='Error',parent=parent,modal=True,destroy_with_parent=True);

        dialog.set_resizable(False);

        label = Gtk.Label();
        if msg is None:
            print(err);
            label.set_text('An error has occured. Exiting the application');
        else:
            print(err);
            label.set_text('Error Message :'+msg);
        label.set_line_wrap(True);
        label.set_max_width_chars(50);
        label.set_justify(Gtk.Justification.CENTER);
        dialog.vbox.add(label);

        dialog.vbox.props.margin_top = 20;
        dialog.vbox.props.margin_bottom = 20;
        dialog.vbox.props.margin_left = 20;
        dialog.vbox.props.margin_right = 20;

        dialog.show_all();
        dialog.run();
        
        if quit:
            exit(1);
        else:
            pass;
       

def handler(signum, frame):
    print("\nExiting Application....");
    exit(1);

try:
    signal.signal(signal.SIGINT,handler);
    app = LoadFlowApp();
    app.main(); 
except Exception as err:
    self.msglog(err);
