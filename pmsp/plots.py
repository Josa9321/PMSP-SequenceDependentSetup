import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta


def gantt_chart(original_df: pd.DataFrame, setup_idx=1, due_date_idx=-1):
    solution_df = original_df.copy(deep=True)
    now = datetime(year=1970, month=1, day=1)
    solution_df['Start'] = [now + timedelta(seconds=t) for t in solution_df['Start']]
    solution_df['Finish'] = [now + timedelta(seconds=t) for t in solution_df['Finish']]
    solution_df['Task'] = [txt for txt in solution_df['Task']]
    solution_df['Machine'] = [f'Machine {h}' for h in solution_df['Machine']]

    fig = px.timeline(solution_df, x_start="Start", x_end="Finish", y="Machine", color='Type', text='Task')
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
    fig.update_layout(
                      plot_bgcolor="white",
                      paper_bgcolor="white",
                      xaxis=dict(tickformat = '%s'),
                      yaxis_title = r'',
                      legend=dict(
                                  yanchor="top",
                                  y=1.2,
                                  xanchor="center",
                                  orientation="h",
                                  x=0.5
                                  ))
    
    fig.update_xaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_yaxes(showline=True, linewidth=2, linecolor='black')
    fig.update_traces(textposition='inside')
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    for n in fig.data:
        n["marker"]['line']["color"]='#000000'
        n['marker']['line']['width'] = 2
        n['marker']['color']='rgba(0, 0, 0, 0)'
        
    
    if setup_idx != -1:
        fig.data[setup_idx]['marker']['color']='#D6DEE2'#'#CDDFF8'

    if due_date_idx != -1:
        fig.data[due_date_idx]["marker"]['line']["color"]='#D21404'
    return fig
    



